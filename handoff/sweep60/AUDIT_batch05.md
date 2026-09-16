# sweep60 batch05 audit — feats.py, ledger_guard.py, estate.py, autostart.py, coverage.py, snapshot.py, context_budget.py, scale_theories.py

All 8 files read in full, uncapped (6,583 lines total: feats.py 2798, ledger_guard.py 1083,
estate.py 723, autostart.py 613, coverage.py 456, snapshot.py 376, context_budget.py 319,
scale_theories.py 215). No sampling.

This codebase carries an unusually large volume of prior self-remediation (each historical bug
named with an order id and explained at length). The findings below are things that are still
live today, verified either by direct code-tracing or by actually running the logic against the
real data file in the tree.

---

## FINDING 1 — HIGH — ledger_guard.py:231-238 — the Open/Resolved duplicate-bug-id check is
currently disabled by a decoy substring, and always reports zero duplicates

```python
231:        marks = sorted((text.find(s), s) for s in ("## Open", "## Resolved", "## Watching")
232:                       if text.find(s) >= 0)
233:        span = {}
234:        for n, (at, sec) in enumerate(marks):
235:            span[sec] = text[at:(marks[n + 1][0] if n + 1 < len(marks) else len(text))]
236:        op, res = span["## Open"], span["## Resolved"]
237:        both = sorted(set(re.findall(r"\[([Mm]\d+)\]", op))
238:                      & set(re.findall(r"\[([Mm]\d+)\]", res)))
```

This code was written specifically to replace an earlier version that assumed an "Open" section
always precedes "Resolved" in the file and sliced `text[i:j]` on that assumption — the code's own
comment two lines above this block says the old version's flaw was "the one check that exists to
catch a bug filed in two places passes even when every Resolved bug is still sitting in Open...
A check that cannot fail reads exactly like a check that passed." The fix locates each heading
with `text.find(s)` instead of assuming order.

**The bug: `str.find()` is a plain substring search, not a line-anchored heading search.** It
returns the position of the *first* occurrence of the literal text `"## Resolved"` anywhere in
the document — including inside prose that merely *mentions* the heading in backticks, which is
exactly what `BUGS.md` does. Verified by reading the live file:

```
BUGS.md:7:    ## Open
BUGS.md:14:   > **76 entries moved** to `## Resolved (paper trail)`, under a heading naming this pass, each block
...
BUGS.md:1543: ## Resolved (paper trail)
```

Line 14 — inside a blockquote describing a *previous* bulk-resolution pass — contains the
literal substring `` `## Resolved (paper trail)` `` a full 1,529 lines before the real
`## Resolved` section heading at line 1543. `text.find("## Resolved")` returns the position of
the line-14 decoy, not the real heading.

I verified this is not merely theoretical by running the exact algorithm against the live
`BUGS.md` on disk:

```
marks: [(264, '## Open'), (669, '## Resolved'), (127654, '## Watching')]
## Open span length: 405
## Resolved span length: 126985
ids found in computed op span: 0
ids found in computed res span: 38
intersection (would be reported as duplicate): []
```

Because the decoy `"## Resolved"` sits only 405 characters after the real `"## Open"` heading,
the code's computed `op` span is truncated to those 405 characters (containing zero bug ids),
and the computed `res` span balloons to 126,985 characters — which is actually almost the whole
of the real **Open** section's content, not the Resolved section's. The intersection check
`ids_open & ids_res` is therefore comparing "nothing" against "the real Open section", and can
never report a hit **regardless of whether a bug id genuinely appears in both the true Open and
true Resolved sections.**

This is the exact "a check that cannot fail looks exactly like a check that passed" failure mode
this file's own docstring and this function's own inline comment name as the reason this code
exists, reintroduced by the fix meant to prevent it, and it is live in the current tree: this
function runs on every `assert_intact()` call, i.e. before every `publish.push()`.

**What input triggers it:** any time `BUGS.md`'s prose (change-log entries, run summaries, etc.)
mentions the literal string `"## Resolved"` or `"## Open"` in backticks or plain text before the
real section heading it is discussing — which is already true of the live file and has evidently
been true for some time (the decoy text describes a bulk-resolution pass, i.e. normal narrative
content for this ledger).

**Confidence:** VERIFIED — both by reading the surrounding code/comments and by executing the
exact span-computation logic against the live `BUGS.md` in the repository (shown above).

**Suggested fix direction (not applied — audit only):** anchor the heading search to line starts
(e.g. `re.finditer(r"^## (Open|Resolved|Watching)\b", text, re.M)`) instead of `str.find()`, so a
heading is only recognized when it actually opens a line, the same discipline
`_handoff_journal_problems()` already uses a few functions later in this same file for
`HANDOFF.md`'s heading detection.

---

## FINDING 2 — MEDIUM (suspected, not executed) — feats.py:186-201 — `_throttle()` iterates
`_BACKOFF` without a lock that covers all its writers, risking a `RuntimeError` under real
concurrency

```python
178: def _throttle(host):
...
186:    dom = registrable_domain(host)
187:    with _HOST_LOCKS[dom]:
188:        base = _pause_for(dom)
191:        mult = _BACKOFF.get(host, 1.0)
192:        for h, m in _BACKOFF.items():
193:            if m > mult and registrable_domain(h) == dom:
194:                mult = m
```//
and, elsewhere:
```python
234: def note_throttled(host):
...
245:    with _HOST_LOCKS[registrable_domain(host)]:
246:        _BACKOFF[host] = min(BACKOFF_MAX, _BACKOFF.get(host, 1.0) * BACKOFF_GROWTH)
```

`_HOST_LOCKS` is a `defaultdict(threading.Lock)` keyed by *registrable domain*, so two different
domains use two different, independent lock objects (this is deliberate and documented — the
whole point of the 2026-09-08 "Traffic on the Fandom edge" ruling was to move locking from
per-host to per-domain). But `_BACKOFF` itself is one global `dict` shared across *every* domain,
and `_throttle()` iterates `_BACKOFF.items()` in full (line 192) while holding only the lock for
`dom` — the domain of the *host being throttled right now*, not a lock over the whole dict.

`roll()` runs with up to 12 workers (`overnight.py` launches `--workers 12`) hitting many
different wikis (domains) concurrently. If thread A is inside `_throttle()`'s loop over
`_BACKOFF.items()` for domain X (holding `_HOST_LOCKS[X]`), and thread B calls
`note_throttled(host_on_domain_Y)` for a host that has never been throttled before — first
insert of a **new key** into `_BACKOFF` — thread B acquires the *different* lock `_HOST_LOCKS[Y]`
and does `_BACKOFF[host] = ...`, which changes the dict's size. CPython raises
`RuntimeError: dictionary changed size during iteration` when a dict is mutated (size changed)
while something else holds an active iterator over it, and there is nothing here that prevents
that: the two threads are synchronized on different locks and neither ever locks the other out
of `_BACKOFF` itself.

This would surface as an intermittent `RuntimeError` from inside `_throttle()`, most likely early
in a roll when many distinct hosts are throttled for the first time in quick succession across
many workers — i.e. exactly the "eight/twelve workers on wikis with no shared lock" scenario this
same file's `_HOST_LOCKS` refactor was written to make safe. Note that `_COUNTS_LOCK` in this
file exists specifically to guard `_RATE_LIMITED` and `_CAP_BOUND` for the identical reason
(read-modify-write races under `roll()`'s concurrency) — `_BACKOFF`/`_STRIKE` do not have an
equivalent dict-wide guard, only the per-domain one, which is not the same lock two different
domains ever share.

**Confidence:** SUSPICIOUS / unverified by execution — I traced the lock scoping carefully
(`_HOST_LOCKS[dom]` is per-domain, `_BACKOFF` is one shared dict, and the loop at line 192 walks
the whole dict) and believe this is a genuine race, but I did not reproduce the `RuntimeError`
under load; it is timing-dependent and would only fire when two different-domain hosts are
throttled at nearly the same instant. Flagging as a real but probabilistic concurrency hazard
rather than a certain one.

---

## FINDING 3 — LOW/uncertain — estate.py:463-472 — the M0–M2 "no rung named" erratum check uses
an aggregate any-word overlap across all three bands and all seventeen rungs, which is looser
than the erratum it is meant to detect

```python
463:    low = "; ".join((band_rows[b] or "").strip() for b in ("M0", "M1", "M2")).lower()
464:    rung_words = {w.lower() for _, r in rung_rows for w in re.findall(r"[A-Za-z]{4,}", r)}
465:    if not any(re.search(r"\b" + w + r"s?\b", low) for w in sorted(rung_words)):
466:        note("charter erratum (open)",
467:             f"M0-M2 ({low}) name no rung of the Ladder at all, so the three lowest bands sit "
468:             f"below rung 1 ({rung_rows[0][1]}) and the shelfmark has no address for what they "
469:             f"threaten")
```

This is the "fourth erratum" check, correctly designed (per its own detailed docstring) to be a
real test rather than a string-presence check on the raw charter text. But the test it performs
is: does *any* four-or-more-letter word from *any* of the 17 rung names appear *anywhere* in the
combined text of M0, M1 and M2's "Can threaten..." column? A single coincidental word match
anywhere in that combined text (e.g. a common English word that happens to also be a substring
of some rung's descriptive name — the rung names are drawn from ordinary words like "Planet",
"Star", "System") would silence the whole erratum, even though the actual defect (none of M0/M1/
M2 individually threatens a real ladder rung) would still be true. The check is an aggregate
"any word, any band" test standing in for what the erratum is actually about ("does this specific
band's own text name a rung"), so a charter edit that happens to introduce one incidental
overlapping word anywhere in M0–M2's text — without actually fixing the substantive gap — would
make this row disappear from the report.

Today this is inert: the current charter text for M0-M2 (per the finding's own printed detail,
"a village; a city or nation; a continent") does not overlap any of the 17 rung names' words, so
the erratum currently prints correctly. This is a forward-looking correctness gap in the check's
precision, not a currently-wrong report.

**Confidence:** Verified the logic reads as described; UNSURE whether this rises to the bar of
a reportable defect since it does not currently misfire — flagging per the instruction to report
uncertain findings labelled as such, rather than omitting a real weakness in a "check that cannot
fail" candidate.

---

## Files with no findings

- **autostart.py** (613 lines) — read in full. The tri-state alive/dead/unknown handling,
  the twin-watchdog detection, the start-budget arithmetic (`_start_decision`), and the
  install/uninstall verdict paths were all traced and are internally consistent with their
  extensive inline documentation. No tautological check, fail-open guard, or truncation found.
- **coverage.py** (456 lines) — read in full. The CITED > READ > NO PAGE > UNREACHABLE >
  NOT ATTEMPTED precedence logic in `state_of()` was traced against its own documentation and is
  correctly implemented (including the "later READ candidate must not discard an earlier one's
  page count" fix). No issues found.
- **snapshot.py** (376 lines) — read in full. Containment checks (`_rel`, `_safe_join`),
  the directory-verify path (`_dir_matches`), and the manifest/restore/verify triangle were
  traced end to end. No issues found.
- **context_budget.py** (319 lines) — read in full. Token/char arithmetic in
  `content_budget_chars`, `measure`, and `feats_block_budget` was checked against the documented
  measurements and is consistent. No issues found.
- **scale_theories.py** (215 lines) — read in full. This module is explicitly documented as
  unwired/dead (held for a future phase per an owner ruling, zero callers repo-wide) — that is a
  known and already-declared state, not a new finding. `surviving_theory()`'s arity assertion and
  `bulk_export_beta()`'s arithmetic are both correct.

---

## Coverage note

Recorded via `sweep_plan.record('sweep60', [...], batch=5)` after this report was written — see
the driving instructions for the exact command used.
