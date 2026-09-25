# sweep61 batch14 — audit report

Scope (all under `src/`, read start to finish, in full, no sampling):

| module | lines |
|---|---|
| hostcheck.py | 1713 |
| health.py | 1319 |
| liveness.py | 1060 |
| thread_integrity.py | 721 |
| tiers.py | 555 |
| citecheck.py | 455 |
| cosmography.py | 375 |
| entity_match.py | 319 |

Total ~6,517 lines, all read in full.

## Summary

This batch is exceptionally heavily audited already — every module carries dense inline
documentation of prior findings (order IDs, sweep numbers, owner rulings) for the exact classes
this brief asks to look for: tautologies, fail-open guards, caps, false comments, dead code. Most
candidate issues I traced turned out to be already-fixed-and-documented, or explicitly named as a
known/declared limitation. I confirmed several docstring claims against the source with grep
rather than taking them on faith (see below).

Two SUSPECTED findings below are new (not mentioned in either module's own commentary). Nothing
VERIFIED-live was found in this batch; both suspected items are latent/edge-case rather than
actively wrong on today's data, which I could not independently re-derive under the read-only /
no-network rule.

## Findings

### 1. `liveness.py`, `_function_line_ranges()` — SUSPECTED, real bug, currently latent

```python
def _function_line_ranges(path):
    ...
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = (node.lineno, getattr(node, "end_lineno", None) or node.lineno)
    return out
```

This keys the returned map by **bare function name**, not by a class-qualified label the way the
sibling `_defs()`/`_classdefs()` passes in the same file do (both of those carry a dotted
`ClassName.method` label specifically because two methods in different classes can share a name).
`ast.walk` visits methods too, so if a module in `GATE_MODULES` defined two functions/methods with
the same name in different scopes, the second one encountered would silently overwrite the first
in `out`, and `reachability()`'s `DECLARED_UNREACHABLE` lookup (`ranges.get(fn_name)`) could then
mark the wrong function's line range as "declared unreachable" — the exact "check that cannot
fail" shape this file exists to catch, reproduced in its own reachability instrument.

Verified by reading `reachability()` (uses `ranges.get(fn_name)` keyed the same way) and by
grepping `escalation.py` (the only module in `GATE_MODULES` today) for duplicate def names:

```
$ grep -n "^    def \|^def " escalation.py | ... | sort | uniq -c
```
— no duplicates found, so this is **not live today**. It is a real gap that would silently
mis-scope a declared-unreachable ruling the moment `GATE_MODULES` is widened (which the module's
own docstring says is the intended next step) or the moment escalation.py gains two same-named
methods. QUESTION for the owner: worth qualifying `_function_line_ranges`' keys the same way
`_defs`/`_classdefs` already do, before `GATE_MODULES` grows.

### 2. `hostcheck.py`, `probe()` (API branch) — SUSPECTED, minor, unverified against live data

```python
pages = ((d.get("query") or {}).get("pages") or {})
live = [p for p in pages.values() if "missing" not in p and int(p.get("pageid", 0)) > 0]
...
return {"host": host, "probed": len(names), "hits": len(live), "rate": round(len(live) / len(names), 3), ...}
```

The query is sent with `redirects: 1`. MediaWiki's `action=query` dedupes its `pages` result by
**final resolved page id**, not by input title: if two of the (up to 40) probed names both
redirect to the same target article, `pages` contains only one entry for that shared target, so
`len(live)` undercounts the number of names the host actually recognised (two names, one hit
counted). This would make `rate` (and therefore `lift`, and therefore the `holds`/`partial`/
`WRONG FICTION` verdict) read slightly low for hosts where probed names collapse this way. The
bias is conservative (makes a real host look weaker, not stronger), so it sits below the priority
of a fail-open guard, but it is a real measurement bug in the file whose entire subject is "lift,
measured correctly, is the only thing this project may act on."

I could not verify this against live data (no network calls permitted this run per the halt), so
this is reported as SUSPECTED / a mechanism, not a measured discrepancy. Left as a note for a
future sweep that can run `probe()` against a real host and compare hit-count to distinct-title
count.

## What I looked at and ruled out (not reported as findings)

- `hostcheck.py`: the `_land_hosts` compare-and-swap, `null_rate`'s None-vs-zero handling, the
  `score()` verdict ladder, `sweep(--repair)`'s lift-based selection, and `purge()`'s
  gate-then-write ordering are all already correct and already documented as fixed (orders
  e2f0b13c766f, 1b15acd3f7b2, 44ae72489678, a5fd110e3910, and others cited in-file). The
  `PROBE = 40` / `sample=12` / `[:8]` figures are protocol-driven batch sizes and statistical
  sample sizes, not report truncations — Hard Rule 0 does not apply to them, and the file itself
  argues this at length (see `relevance()`'s docstring on the API-vs-RAW sample-size mismatch,
  already named as known).
- `health.py`: the ledger/samples compare-and-swap (`_flush_ledger`, `_flush_samples`), the
  thread-local re-entrancy guard on `flush()`, `check_caches()`'s quarantine/exclusion/small-cache
  logic, and `reopen_stranded()`'s re-read-before-write guard are all sound and already documented
  at length in-file.
- `liveness.py`: cross-checked the receiver-aware DEAD pass, the module-dead pass, and the
  PHANTOM pass's documented known-under-report (module-wide `defined` set) — all as described,
  nothing further found. The `_function_line_ranges` gap above is the one thing not already
  covered by this file's own commentary.
- `thread_integrity.py`: `classify()`'s dedup (`(b, a) in seen`), the DANGLING/PARTIALLY-DANGLING
  split, and `_floor_verdict()`'s ratchet-only-down logic all check out.
- `tiers.py`: the CUTS/MULTIVERSE_THRESHOLD raised invariants, the containment (`split_sources`)
  gate before publish, and the two-hyperverse-measurements disclosure are all correct and
  consistent with what `main()` actually prints.
- `citecheck.py`: `_classify`, `_mention_kind`'s quote/disclaimer scoping, and `_in_tree_lead`'s
  path-lead detection all check out against their stated rules.
- `cosmography.py`: verified by grep that `GALAXIES_CONSELICE_2016` and `STARS_MILKY_WAY` are
  genuinely read by nothing else in the tree, confirming the "REFERENCE ONLY (grep-verified)"
  comments are accurate rather than stale. `validate()`'s Kardashev ceilings and the
  `SIZE_CLASS_MAX_GALAXIES` category check are correctly derived from their own descriptions.
- `entity_match.py`: `qualifier_compatible()`'s absolute gate, the `STRONG`/`WEAK` raised ordering
  check, and `candidates()`'s uniform return shape (the `blocked_by_qualifier: {}` fix) all check
  out. Confirmed `MatchReason` is indeed a bare constant namespace with no methods, matching the
  claim made about it in `liveness.py`'s own docstring.

No tautologies, no fail-open guards, no new caps/truncations, and no dead code were found beyond
what each module already documents as known and handled. No false comments were found beyond the
two claims above (cosmography.py) that were checked and found accurate.
