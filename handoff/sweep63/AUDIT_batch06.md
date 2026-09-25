# sweep63 batch06 audit

Scope (read start to finish, in chunks, no sampling; line counts from `wc -l` at time of reading):

- `src/workorders.py` -- 2507 lines. Read in full (1-700, 700-1400, 1400-2100, 2100-2507).
- `src/rigor.py` -- 1132 lines. Read in full (1-600, 600-1132).
- `src/identity.py` -- 752 lines. Read in full, one pass.
- `src/feats_index.py` -- 628 lines. Read in full, one pass.
- `src/reference.py` -- 497 lines. Read in full, one pass.
- `src/genre.py` -- 385 lines. Read in full, one pass.
- `src/deprecated/catalogue_local.py` -- 333 lines. Read in full as source (self-refusing:
  raises `SystemExit` at import except for `--help`).
- `src/resonance.py` -- 298 lines. Read in full, one pass.

Total: 6,532 lines across 8 modules, all read in full, no sampling.

## Context and prior coverage

CLAUDE.md's doctrine (Hard Rule -1 escalation/halt, Hard Rule 0 no caps, fail-closed, "a check
that cannot fail looks exactly like a check that passed") was read first. All eight modules here
overlap almost exactly with sweep61's batches 03, 06, 07, 09 and 13, which already audited this
same code start to finish. Those five audits were read in full before this pass and are not
re-summarised; their findings (an `overwatch.py` digest-retirement bug, a `pipeline.py` dropped
`physiology` field, a `standards.py` 700-byte-head truncation, a `codewatch.py` interpreter-flag
mis-parse, a `scout.py --limit 0` truthiness bug) are all in modules OUTSIDE this batch's scope
and are not repeated here. Within this batch's own eight files, sweep61 filed no findings except
one QUESTION each in `rigor.py` (`adjudication_beta`'s `k = max(1, ...)` clamp at n_laws_touched
== 0, still dormant, no caller reaches it) and `resonance.py` (no production caller, already
stated in the module's own docstring) -- both re-checked here and unchanged; not re-filed.

The code is heavily self-documented with order ids for past fixes. Per the brief, shapes the
comments already name and handle are not re-reported below.

## Findings

### 1. VERIFIED -- `feats_index.py`, `feats_for_source()` (~lines 363-375): a `doc:`-bound
source is reported through the `binding` out-channel as `"kind": "bound"`, contradicting the
function's own docstring and `source_binding()`'s classification of the identical source

```python
idx = load_index()
host_map = host_to_sources()
hosts = [h for h, srcs in host_map.items() if source_name in srcs]
if not hosts:
    kind = source_binding(source_name, host_map)
    if binding is not None:
        binding.clear()
        binding.update({"kind": kind, "hosts": []})
    _UNBOUND_ASKED[source_name] = kind
    return []
if binding is not None:
    binding.clear()
    binding.update({"kind": "bound", "hosts": sorted(hosts)})
```

`host_to_sources()` (lines 152-192) inverts `data/WIKI_HOSTS.json` and filters out only the
`"pages:"` sentinel (`not host.startswith(_PAGES_SENTINEL)`); it deliberately does NOT filter
`"doc:"` pseudo-hosts (owner-supplied ingested documents, e.g. `data/WIKI_HOSTS.json`'s
`"Arcanum Worlds (Odyssey of the Dragonlords)": "doc:arcanum-worlds-odyssey-of-the-dragonlords"`)
-- `source_binding()`'s own docstring says so explicitly: "`host_to_sources` strips the `pages:`
sentinels ... A source bound to one is not in the map at all ... Asked of the raw file" (i.e.
`doc:` stays IN the map, `pages:` does not).

The consequence: for a source bound to a `doc:` host, `hosts` in `feats_for_source` is
NON-empty (it contains the literal string `"doc:..."`), so the `if not hosts:` branch --
the only place this function ever calls `source_binding()` -- is skipped entirely, and the
`kind` is hardcoded to `"bound"` without consulting `source_binding()` at all. This directly
contradicts the function's own docstring one paragraph above: "Pass a dict and it is stamped
with `{"kind": ...}` from `source_binding`" -- that is only true on the empty-hosts path.

Verified by direct execution against the live corpus (read-only; `feats_for_source` performs no
writes):

```
source_binding("Arcanum Worlds (Odyssey of the Dragonlords)")  -> "doc"
feats_for_source("Arcanum Worlds (Odyssey of the Dragonlords)", {"entries": []}, binding=b)
  -> b == {"kind": "bound", "hosts": ["doc:arcanum-worlds-odyssey-of-the-dragonlords"]}
```

For contrast, a genuine `"pages:"` source (`"A Plethora of Paladins"`) is classified correctly
as `{"kind": "pages", "hosts": []}`, precisely because `host_to_sources()` filters `pages:` out
of its map, forcing that source down the `if not hosts:` / `source_binding()` branch. `doc:` gets
no equivalent filter, so it falls into the opposite, un-consulted branch. The asymmetry is the
bug: the two pseudo-host sentinels are handled by two different code paths that happen to agree
for `pages:` and disagree for `doc:`.

**Live impact today:** dormant/non-observable, not a currently-wrong report. Grepped every
consumer of `feats_for_source(..., binding=...)`: the only caller is
`manifest_builder.py:378-386`, and it only branches on `_binding.get("kind") == "unbound"` (its
own comment lists all four kinds -- bound/pages/doc/unbound -- and says a warning is deliberately
suppressed for `pages`/`doc`/`bound` alike, "an alarm that always sounds is furniture"). Since
neither `"bound"` nor `"doc"` triggers that warning, today's single call site produces the same
visible output either way. The defect is real and concretely traced, not hypothetical: it
violates the function's own stated contract, it disagrees with `source_binding()`'s and
`binding_report()`'s classification of the same source, and it would misinform any future
caller (or a manifest_builder change extending the four-way distinction the comment already
enumerates) that inspects `binding["kind"]` for a `doc:`-bound source.

Verified by: reading `host_to_sources`'s filter (only `_PAGES_SENTINEL`), reading
`feats_for_source`'s branch structure, reading `source_binding`'s own docstring describing the
asymmetry it relies on, and confirming both by direct read-only execution against the live
`data/WIKI_HOSTS.json` (one `doc:` source and several `pages:` sources on file today).

Suggested fix (not applied -- read-only batch): in `feats_for_source`, when `hosts` is
non-empty, still classify each host by prefix (or simply call `source_binding()` unconditionally
and let it decide `bound` vs `pages` vs `doc`) rather than hardcoding `"bound"` -- e.g. derive
`kind` from whether any host in `hosts` starts with `"doc:"`/`"pages:"`, matching the vocabulary
`source_binding()` already defines, so the two functions cannot disagree about one source.

## Other observations (not filed as findings)

- `workorders.py`: re-verified the `_fire()` polarity fix, the `where`-identity contract in
  `order_id`/`file_order`/`reroute`, the compare-and-swap retry in `_mutate`, and every
  `sweep_detectors()` section's `_fire`/`_detector` wiring. All read/traced end to end; nothing
  new found beyond what the surrounding comments already document as fixed (the `overwatch.py`
  digest-retirement bug sweep61-batch06 found is in a module outside this batch and does not
  recur here). `local_agent._denied_target()` matches on basename only
  (`base = rel_l.rsplit("/", 1)[-1]`), so `file_order`'s LOCAL-denylist door-guard is unaffected
  by whatever directory prefix a `where` target carries -- checked because it looked like a
  possible mismatch with `where_targets()`'s own `src/`-stripping normalisation, but the two
  never need to agree since the denylist check is basename-only by construction.
- `identity.py`: `continuities()` and `main()`'s `--host` branch both do
  `for k in _inv_keys(host): if inv.get(k): counts = inv[k]; break` -- since `mine()` can
  legitimately store an EMPTY dict for a host with zero designators, a falsy-but-present first
  key falls through to the next spelling in `_inv_keys` rather than stopping on "found, empty".
  In practice this can only produce a wrong answer if two of the three fallback spellings
  (`cachekey.host_dir(host)`, the bare host, the hand-folded spelling) both exist as SEPARATE
  keys in the inventory for different hosts, which is not observed in the current cache and is
  not a shape `mine()` constructs (each host is mined under exactly one directory/key). Traced
  but not filed as a finding -- no concrete reachable harm found, flagged as a QUESTION below
  instead of VERIFIED/SUSPECTED.
- `rigor.py`: `adjudication_beta`'s `k = max(1, min(n_laws_touched, M))` clamp still forces
  `k >= 1` at `n_laws_touched == 0`, the same dormant QUESTION sweep61-batch07 recorded (no
  caller in the tree passes 0; `main()`'s `_AUDIT_ROWS` and `verify_math.py`'s call sites all use
  `laws >= 1`). Not re-filed. `bradley_terry`'s Ford's-condition refusal, `perron_weights`'/
  `logrank_weights`' two-sided CR/`|cr|` checks, and `_validate_reciprocal_matrix`'s guards were
  all re-traced; no new issue.
- `genre.py`, `reference.py`, `resonance.py`: re-verified the Hard-Rule-0 uncap fixes
  (`classify_text`'s `top=None` default, `classify_source`'s refusal of a numeric `cap`,
  `reference.py`'s calibration-gates-the-exit-code fix, `resonance.py`'s Gauss-Seidel convergence
  fix and its `no_evidence`/`converged` separation) against the current source; all intact, no
  regression. `resonance.py` still has zero production callers, as its own docstring and
  sweep61-batch13 both already state -- not re-filed.
- `deprecated/catalogue_local.py`: unchanged self-refusing module (`raise SystemExit(_REFUSAL)`
  at import time except `--help`); matches sweep61-batch09's account exactly. No new finding.
- No tautologies, fail-open guards, or Hard-Rule-0-style caps/truncations were found beyond what
  is already documented as fixed in these eight files' own comments. No regex/escape corruption
  found (`_BAD_CHARS` transit guards present and intact in every file that carries one). Nothing
  found that touches `prose_enabled`/`step4_enabled` or any halt-lifting path -- none of these
  eight modules call `escalation.clear()` or touch those flags.

## Questions (not findings)

- `identity.py`'s `_inv_keys` fallback-key iteration (above): worth a future pass confirming no
  two hosts' inventory keys can ever collide across the three spellings, or making the loop stop
  on "key present" rather than "value truthy" so an intentionally-empty host can't fall through.
  Low confidence of live harm; not filed as SUSPECTED.

## Summary of findings by kind

- Checks that cannot fail: 0 new.
- Fail-open guards: 0 new.
- Caps/truncations (Hard Rule 0): 0 new.
- Real logic bugs (category 4): 1 VERIFIED -- `feats_index.py` `feats_for_source()` mislabels a
  `doc:`-bound source's `binding["kind"]` as `"bound"` instead of `"doc"`, contradicting its own
  docstring and `source_binding()`'s classification of the same source. Currently dormant (the
  one live caller does not branch on the distinction) but concretely wrong and traced by direct
  execution against the live corpus.
- Halt-lifting / prose_enabled / step4_enabled paths: 0 found.
- Regex/escape corruption: 0 found.

## Coverage

Recorded via `sweep_plan.record('run63', [...], batch=6)` for all eight modules listed above,
using `deprecated/catalogue_local.py` as the accepted spelling (confirmed against
`sweep_plan.normalise_module`'s docstring, which names that exact form as the one this module
resolves and the bare `catalogue_local.py` as a spelling it does NOT know).
