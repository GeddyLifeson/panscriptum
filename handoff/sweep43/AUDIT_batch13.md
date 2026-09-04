# Audit — run43, batch 13

Files read in full: `src/read.py`, `src/overwatch.py`, `src/derivation.py`, `src/sweep_plan.py`,
`src/tiers.py`, `src/sweep.py`, `src/coverage.py`, `src/cosmology_graph.py`.

Method note: every candidate below was re-checked against the exact source lines before being
kept. Several plausible-looking "bugs" were reasoned through and DISPROVED rather than filed —
notably a suspected gap in `tiers.py`'s containment scan (the early `continue` on
`xenoverse is None`), which turns out to be logically safe once you account for the fact that a
multi-member complete-linkage multiverse group's internal edges necessarily clear the (looser)
xenoverse threshold too, so no violation can be missed by that skip. Recorded here so the next
sweep doesn't re-spend time on it.

`derivation.py`'s `check_graph()` was also run live: `VERDICT: LEDGER CLOSES`, zero problems.

---

## src/coverage.py

### MAJOR — unguarded read of the (documented) racy host map
`src/coverage.py:187`
```python
hosts = json.load(open(F.HOSTS, encoding="utf-8"))
```
No try/except at all. `F.HOSTS` (`data/HOSTS.json` or equivalent) is the exact file `read.py`
goes out of its way to protect against a race on: `read.py`'s `queue()` (same corpus, same file)
retries up to 4 times with backoff and then `raise SystemExit(...)` rather than silently treating
a transient read failure as "no hosts", with the comment "the host map has three writers... a
racing write is unreadable for milliseconds, not seconds. Anything that outlasts four attempts is
a real fault." `coverage.py`'s `measure()` reads the identical file with zero protection. If this
races with one of the documented writers, `measure()` raises an unhandled `JSONDecodeError` (or a
transient `PermissionError` on Windows) and the whole coverage pass crashes rather than degrading
gracefully or retrying — this is pipeline-critical: `coverage.py`'s own module docstring says
`COVERAGE.json` is "read by the dashboard, standards, allsweep and the published page."
**Remedy:** wrap this read in the same retry+fail-closed pattern `read.py:queue()` already uses
for the same file (or factor it into a shared helper both modules call).

### MINOR — unmarked source-name truncation in three console panels
`src/coverage.py:240`, `:252`, `:267`
```python
print(f"   {r['entries']:>6,}  {r['source'][:58]}")                      # :240
...
print(f"   {r['coverage']:>6.1%} cited  {r['settled']:>6.1%} settled  "
      f"{r['entries']:>6,} entries   {r['source'][:44]}")                # :252
...
print(f"   {r['coverage']:>6.1%} cited  {r['feats']:>6,} feats  "
      f"{r['entries']:>6,} entries   {r['source'][:44]}")                # :267
```
Every one of these slices the source name — the row's identity — with no ellipsis and no "cut"
marker. This is the exact class of defect the codebase has already gone through and fixed twice
in sibling files in this same batch: `cosmology_graph.py` built a dedicated `_cut()` helper
specifically because "a display-side cut... refuses it when nothing says the cut happened," citing
the real corpus source name `'Who Framed Roger Rabbit (incl. all content from its associated
crossover-toon IPs)'` as the concrete case that broke silently; and `sweep.py`'s own comment (same
batch, ~line 304) says explicitly "The source name is no longer cut either... it is the identity
of the row a person acts on" — and its "BIGGEST GAPS" / "REACHED BUT SILENT" panels print `{s}`
uncut. `coverage.py`'s three panels (`SOURCES WITH NO WIKI HOST`, `WORST COVERED WITH A HOST`,
`BEST COVERED`) were apparently missed by that pass. This is the "lesser instance" per the audit
brief — `COVERAGE.json` on disk holds the full name — but a person reading the console output
cannot tell a truncated name from a genuinely short one, and cannot always distinguish two
different long sources that happen to share a 44/58-character prefix.
**Remedy:** either print the name uncut (as `sweep.py`'s fixed panels do) or route it through a
`_cut()`-style helper that appends a visible marker when it truncates.

## src/tiers.py

### MINOR — same unmarked truncation, on an explicitly uncapped list
`src/tiers.py:403`
```python
for v, a, b, sh in deliberate_joins(w, shared):
    print(f"   {v:>8.0f}  {a[:26]:<28}{b[:26]:<28}{sh}")
```
`deliberate_joins()`'s own docstring is emphatic that this is "THE WHOLE SHARED LIST" and that a
cap here was already found and fixed once (order 9861c18b8485/run #26/#27) because "the function's
own docstring calls this list THE EVIDENCE that a xenoverse is artificial." The row-count part of
that fix landed — every pair is printed, none dropped — but the two source names `a`/`b` are still
silently cut to 26 characters each with no marker, on the very panel titled "why a xenoverse is
'artificial'." Same remedy as above: mark the cut, or don't take it.

## src/overwatch.py

### INFO — two entries of `_STATE_RANK` are unreachable
`src/overwatch.py:303`
```python
_STATE_RANK = {"open": 0, "stale": 1, "confirmed": 1, "refuted": 2, "retired": 2, "closed": 2}
```
Grepped every assignment to `f["state"]` in this file: the only values this module ever writes
are `"open"` (on first sighting), `"closed"` (auto-triage refuted), and `"retired"` (digest
changed). A "confirmed" verdict from `verify_open()` deliberately does NOT change `state` — it
increments `f["confirmed_n"]` while the finding correctly stays `"open"` (still needs fixing).
So `_STATE_RANK["confirmed"]` and `_STATE_RANK["stale"]` can never be looked up by
`_progress()`'s `str(f.get("state","")).lower()` against data this module itself produces — they
are dead entries in the ranking table this module's own comment calls load-bearing for
`_merge_ledgers`' "further along wins" rule. Not a functional bug today (the reachable states rank
correctly), but it is exactly the "guard on a value that can't occur" shape this audit is asked to
flag, and a maintainer reading `_STATE_RANK` would reasonably conclude "confirmed" is a `state`
this module sets, which it is not. **Remedy:** either drop the two dead entries, or (probably
better, since a hand-edited ledger entry could plausibly carry a legacy/foreign "stale" value)
leave them and say in the comment that they exist for input compatibility, not because this module
writes them.

## src/read.py, src/derivation.py, src/sweep_plan.py, src/cosmology_graph.py

No new findings survived verification in these four. All four are heavily self-documented with
extensive prior fix history (many named "order" hashes), and the logic that history describes was
checked directly against the current code and matches. `derivation.py`'s ledger was additionally
verified live (`VERDICT: LEDGER CLOSES`).

---

## QUESTIONS (for the OWNER, not filed as work orders)

**Q1 — `sweep_plan.py` shard filenames key on run+batch+pid, not run+batch+pid+thread.**
`_shard_path()` (src/sweep_plan.py:131-138) builds `"%s.%d.json" % (safe, os.getpid())` — no
thread id. Every OTHER concurrent-write site read in this batch or cited by it
(`read.py:_chunk_put`, `silence.write_json`'s own temp-name convention, `_local_carded`'s
per-piece calls) deliberately embeds **pid AND thread** specifically because this codebase has
been bitten, repeatedly, by two writers sharing one scratch filename. `record()`'s own docstring
justifies the narrower pid-only key by asserting each batch "since run #28, [runs] in ITS OWN
PROCESS" — which the current dispatch pattern (one subprocess per batch) honors. Is that
assumption meant to be permanently load-bearing (i.e., is it safe to assume `sweep_plan.record()`
is never called from two threads of one process for the same run+batch), or should the filename
carry a thread id too for the same defense-in-depth reason every sibling site now does?

**Q2 — `record()` overwrites rather than merges a given (run, batch, pid)'s own shard.**
If a caller invokes `sweep_plan.record(run, covered, batch=N)` more than once from the same
process for the same batch — e.g. incremental "here's what I've read so far" calls rather than one
final call with the complete list — the second call's shard file replaces the first's outright
(same `_shard_path`), so any module named only in the first call and omitted from the second is
silently dropped from that batch's provable coverage. This is not a bug in the currently-documented
usage (one call per batch with the complete list, as this very batch's own instructions specify),
but nothing in `record()`'s docstring says "pass the full accumulated list every time, not an
increment" — worth stating explicitly given how much of this module's own history is about exactly
this class of silent loss.

---

## Summary

| Severity | Count |
|---|---|
| BLOCKING | 0 |
| MAJOR | 1 |
| MINOR | 3 |
| INFO | 1 |

Findings: coverage.py unguarded HOSTS read (MAJOR); coverage.py x3 unmarked source-name
truncations (MINOR, filed as one order); tiers.py unmarked source-name truncation in
`deliberate_joins` panel (MINOR); overwatch.py dead `_STATE_RANK` entries (INFO).
