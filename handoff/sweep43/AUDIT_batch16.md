# Sweep43 batch16 audit

Files read in full: `src/local_agent.py`, `src/binding_health.py`, `src/identity.py`,
`src/endpoint.py`, `src/worldseed.py`, `src/render.py`, `src/wh40k.py`, `src/propagation.py`.

Two conditions the brief pre-filed and told us not to re-file were confirmed present and are
not repeated here: (a) LOCAL-rung orders whose target is on the DENYLIST are undeliverable, and
(b) `local_agent`'s 503 retry loop (four attempts, ~6 minutes) in `_chat()`.

Overall finding: this is an unusually heavily self-audited codebase. Every one of these eight
modules carries extensive in-line documentation of bugs found and fixed by prior sweeps (case
folding, NTFS ADS, junction bypass, lost-update races, truncation-inside-envelope, etc.), and
line-by-line re-verification of that already-fixed machinery did not turn up a live regression
in it. The two new findings below are both in `binding_health.py`'s `run()`, in code that
postdates most of that hardening.

## src/local_agent.py

No new findings. Read in full, including the write-gate chain (`_safe`, `_denied_target`,
`t_propose_patch`'s allow/deny/protected-region checks, `_gates`, the blast-radius cap,
`_tool_message`'s envelope-safe truncation, and `run()`'s halt check and achievement/exit-code
logic). Traced the interaction between `_safe()`'s junction-aware denylist re-check and
`t_propose_patch`'s separate resolved-spelling allowlist re-check (the two different fixes filed
as "bypass class six" and "bypass class seven") and confirmed they compose correctly: a junction
redirecting into a denied region is caught by `_safe()`; a junction redirecting to an undenied
but non-writable path is caught by `t_propose_patch`'s own `_spellings` check. No gap found
between them.

## src/binding_health.py

### MINOR — `run()` line 1027: `--limit 0` silently means "no limit", not "zero hosts"

`src/binding_health.py:1027-1028`
```
    if limit:
        hosts = hosts[:limit]
```
`limit` comes straight from `argparse`'s `--limit` (`type=int, default=None`). Python's
truthiness makes `0` and `None` the same value to this test, so `--limit 0` does not slice
`hosts` to an empty list — it leaves `hosts` untouched and the run canaries every bound host,
which is the opposite of what a caller asking for zero hosts would expect. Verified directly:
```
limit = 0; hosts = list(range(200))
if limit: hosts = hosts[:limit]
len(hosts)  # -> 200, not 0
```
Nobody is likely to type `--limit 0` by hand, but an automated harness or CI smoke-test that
parameterises this flag (e.g. to assert the CLI's own contract, or as a computed value that can
legitimately evaluate to zero) would get a full ~200-host network sweep instead of a no-op.
Remedy: `if limit is not None:`.

### MINOR — `run()`: a `--host`/`--limit` filter matching zero hosts still re-stamps `BINDING_HEALTH.json`'s freshness with a full merge

`src/binding_health.py:1091` (the only guard against landing a degenerate report) reads:
```
    if not (only or limit) and not out:
```
This guard exists specifically to stop a whole-estate report being replaced by one describing
"a library that is mostly not there" (its own comment, lines 1079-1090). But it is gated on
`not (only or limit)`, so it never fires when `only` or `limit` was given at all — including the
case where that filter matched **nothing** and `out` came back empty (e.g. `--host` given a
hostname that is not a value anywhere in `data/WIKI_HOSTS.json`, a plausible typo, or a source
name passed where a host was wanted). In that case control falls through to the partial-pass
merge branch (lines 1103-1153): `prior` is read from disk, `out` (empty) contributes nothing,
`merged` ends up identical to what was already on disk, and `doc = {"at": time.time(), ...,
"partial_pass": {"probed": [], ...}}` is landed via `_land_cas` (line 1152) — which succeeds,
because nothing else is writing concurrently.

The result: `BINDING_HEALTH.json`'s top-level `at` field advances to "now" even though this pass
verified **zero** hosts. `doc["partial_pass"]["probed"]` is honestly `[]`, so a reader who
inspects that sub-field is not misled — but any downstream reader that treats the top-level `at`
as "how fresh is this report" (the pattern this project uses elsewhere, e.g.
`identity.staleness_banner`'s own "Treat stale counts as a FLOOR" doctrine) would see a report
that looks freshly re-verified when nothing was actually checked. This is the same "smaller
universe wearing the same shape as the real one" failure the module's own `_report_not_written`
guard exists to prevent for the whole-estate case (lines 1010-1017, 1097-1102); the equivalent
protection was never extended to the partial-pass path's degenerate (zero-hosts-matched)
sub-case.

Blast radius is narrow: no host verdict is altered, no quarantine is falsely lifted or imposed.
Rated MINOR rather than MAJOR because the honest `probed: []` field is right there for anyone
who looks, and because this only fires on a filter that matches nothing (typo-shaped, not a
routine invocation).

Remedy: extend the guard at line 1091 (or add one just before the `only or limit` merge branch)
to also refuse — the same way `_report_not_written("BINDING_ESTATE_EMPTY", ...)` already does —
when `(only or limit) and not out`, i.e. when the filter was given but matched no host at all.

## src/identity.py

No findings. Read in full, including the three-test `_is_continuity` predicate (orthography,
population, branching), the incremental staleness repair in `load()`, and the epoch-mandatory
source machinery. One thing checked and NOT flagged as a bug: `_is_continuity`'s final branch
(`n >= 2 and shared >= max(2, 0.5 * n)`, line 234) is only ever reached for `n == 2` in practice,
since `n >= MIN_BEARERS` (3) already returns True earlier and `n == 1` is handled separately —
so the "majority" framing in the docstring collapses to "both bearers of a 2-bearer designator
must be shared" for the one case that survives. This is stricter, not looser, than a literal
50% reading, so it is not a safety gap; noted here only in case a future editor tries to
"simplify" the formula and changes its behaviour for n>=3 by accident (it currently doesn't
matter because that branch is unreachable at n>=3).

## src/endpoint.py

No findings. Read in full, including `_save()`'s and `register()`'s compare-and-swap merge
logic, `detect()`'s DEAD_TTL re-probe gate, and the mode-html section added after the
`if __name__ == "__main__":` ordering bug (order a60c150b6303) was fixed.

## src/worldseed.py

No findings. Read in full, including the `_first()` seeded-fallback provenance tagging, the
Assay-band tier parser (`to_options`, clamped to M0-M10 with an explicit out-of-range note
rather than silent clamping), and `build_all`'s ONOMASTICON/CONTINUITY_GROUPS read-failure
reporting. The "primitive" tech-tier entry flagged in the module's own comment (line ~206-224,
order ad681057369a) as an OWNER QUESTION is a live, already-filed curatorial question, not a new
finding — noted here only for completeness, not re-filed.

## src/render.py

No findings. Read in full, including `children_of`'s prefix-matching fix (order 3270e0172391)
and the caption/span fix in `containment_svg` (order 48c1388144bd). The `[:26]` name truncation
at line 157 is a display-only cut with the full name preserved in `children_of`'s own return
value (documented at line 216-224 as the deliberate, reversible half of a fix that made the
*stored* field uncapped) — this is the Hard Rule 0 "lesser console instance" case explicitly
carved out in the brief, not a violation.

## src/wh40k.py

No findings. Read in full, including the per-axis provenance tagging (`_provenance`) and the
atomic, verdict-checked write at the end of `main()`.

## src/propagation.py

No findings. Read in full, including `load_graph`'s inverse-weight edge dedup, the Dijkstra
implementation in `shortest()` (traced the `src == dst` and disconnected-graph edge cases by
hand), and `observed_mark`'s two-clock (ascension vs arrival) model. Confirmed
`ascension_years(1) == 0.0` makes the trailing `return 0` in `observed_mark` genuinely
unreachable, matching its own comment.

## Questions for the owner

None raised this batch — no ambiguous design/curatorial call was found; the two findings above
are both mechanical.
