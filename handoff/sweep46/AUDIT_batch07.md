# sweep46 — batch 07 — `feats.py` `corpus_db.py` `custodes.py` `policy.py` `canon_backup.py` `retry_synthesis.py` `wh40k.py` `descending_ladder.py`

Read-and-report audit. **No file in `src/` was edited.** `drill.py`, `mutate.py`, `allsweep.py`
and `publish.py` were not run; `feats.py` was read only, never invoked against a real host.

---

## 0. Coverage, stated honestly

All eight modules were read end to end, in full, in the order assigned (~5,586 lines). No file
changed under me mid-read. `feats.py` (1,959 lines) was the only one requiring two `Read` calls
(offset continuation); the two halves are contiguous and both post-nothing-else-changed.

Every finding below was verified against the live source and, where practical, against live
data on disk (`data/SWEEP_ROLL.json`, `data/WIKI_HOSTS.json`, `state/workorders.json`,
`state/workorders_closed.jsonl`) or by direct execution of the function in question. Nothing
below was inferred from a comment alone.

---

## 1. Findings filed

### 1.1 `d1113e987407` — MAJOR / RUN — `feats.resolve_hosts()` can cache a settled "no wiki" with zero probes

`_slugs(source)` (feats.py:629-641) filters every slug candidate to `len(c) > 2`. A source name
that reduces to two or fewer alphanumeric characters after cleaning yields **no candidates at
all**. The guess-and-verify loop in `resolve_hosts()` (feats.py:720-734) is a `for/else`:

```python
undetermined = []
for slug in _slugs(src):
    ...
else:
    if undetermined:
        unprobed[src] = undetermined
        known.pop(src, None)
    else:
        known[src] = None
```

When `_slugs(src)` is `[]`, the loop body never runs, `undetermined` stays empty, and the `else`
falls straight to `known[src] = None` — a **settled negative written for a source that was
never probed once**. This is the identical failure order `64e4db060ad6` was filed and fixed for
three lines above ("A NULL IS A CACHED FAILURE, NOT AN ANSWER") — here it arrives through an
empty candidate list rather than a failed HTTP call, and the safeguard that order built
(`unprobed`, left out of the map, re-asked next run) never engages, because nothing was ever
attempted to be *undetermined*.

**Verified against live data**: computing `_slugs()` over all 215 source names in
`data/SWEEP_ROLL.json` finds exactly one that produces `[]` — **`DC`** (DC Comics; `dc` is two
characters and fails `len(c) > 2`, and no other transform in the candidate tuple survives it
either). This is dormant today only because `data/WIKI_HOSTS.json` already carries
`"DC": "dc.fandom.com"` from before this filter existed — `resolve_hosts()`'s
`if known.get(src): continue` guard skips DC on every run while that entry stands. If
`WIKI_HOSTS.json` is ever rebuilt from nothing, or that key is lost, or a future source is added
with a similarly short name, `resolve_hosts()` writes a `None` for it with zero network activity
— and unlike a probed-and-failed source, **it can never self-correct**, because `_slugs()`
returns `[]` again on every subsequent run. DC is one of the larger sources in the catalogue.

Remedy is mechanical: lower the threshold to `len(c) >= 2`, or route an empty `_slugs()` result
through the same `unprobed` path a genuinely-undetermined probe already takes.

### 1.2 `dfa24eb10b9f` — MAJOR / RUN — `corpus_db.rebuild()` can turn a file-read failure into a whole-corpus false backlog

`rebuild()` loads `data/WIKI_HOSTS.json` and `data/COVERAGE.json` with a bare
`try/except Exception: silence.note(...)`, falling back to `{}` on any failure — missing file,
torn JSON, permission error, or a read racing a concurrent atomic replace. This is **the exact
class of bug this same function was already fixed for** on the spine-code resolver (order
`25266fa8c2dc`, `SPINE_LOOKUP_FAILED`): that fix's own comment describes a whole-file read
failure of `CHARTER_SPINE_CODES.json` making "ALL 216 sources report as unshelved... a
whole-roll curatorial backlog... nearly acted on as one." The identical mechanism is live and
unfixed for the other two lookup files:

- A `WIKI_HOSTS.json` parse failure → `hosts.get(src)` is `None` for every source → the
  `hostless` canned query (`WHERE host IS NULL`) reports the **entire catalogue** as hostless.
- A `COVERAGE.json` parse failure → `cited` is `None` for every source → `unmeasured` and
  `worst_cited` both misreport the whole corpus.

Neither failure is named in `meta`, printed by `--rebuild`, or surfaced in
`_freshness_banner()` the way `unreadable_records` / `unreadable_evidence` /
`spine_lookup_failures` already are (all three of which sit a few dozen lines below this exact
gap, in the same function, having been fixed for exactly this reason).

Remedy: extend the already-established `SPINE_LOOKUP_FAILED` three-state pattern (built in this
same function, for this exact failure class) to the host map and the coverage map.

### 1.3 `3465775cc2ca` — MINOR / RUN — `descending_ladder.shrink_report()` accepts a non-physical mass and reports it lawful

`shrink_report()` guards `to_m <= 0` but never guards `mass_kg <= 0`, unlike its sibling
`transgression_bits()` in the same file, which was explicitly fixed for this input class (order
`2d6252e03485`, "A NON-PHYSICAL TRAJECTORY IS REFUSED, NOT PRICED AT ZERO"). Reproduced directly:

```
shrink_report(mass_kg=0,  from_m=1.0, to_m=1e-10) -> mass_conserved_is_lawful: True
shrink_report(mass_kg=-5, from_m=1.0, to_m=1e-10) -> mass_conserved_is_lawful: True
```

Both return a confident "lawful" verdict with `objections: []` and `input_error: None` — for
zero or negative mass, which the sibling function in this same file explicitly refuses as a
caller error rather than pricing at zero. The mechanism is identical to what was already fixed:
`density_at_scale(mass_kg<=0, ...)` returns a non-positive `rho` that clears the saturation
check, and `schwarzschild_radius(mass_kg<=0)` returns a non-positive `r_s` that no positive
`to_m` falls below, so both objection tests are silently defeated.

**Dormant, and said plainly**: `descending_ladder.py` has zero production callers anywhere in
`src/` — already tracked separately at order `66f96febdb3a` (OWNER rung). Nothing downstream is
fed this bad verdict today. Filed anyway because it is a real, verified, reproducible defect
that mirrors an already-fixed sibling bug in the same file, and it should be closed before the
module is ever wired up rather than rediscovered live.

### 1.4 `f5ffb9979a07` — MINOR / RUN — `canon_backup.verify()` conflates "could not read" with "content changed"

`verify()`'s `changed` list is built as
`[r for r, d in live.items() if recorded.get(r) and d != recorded[r]]`, where `live[r]` comes
from `digest(p)`, which returns `None` on any `OSError` (a reader/writer holding the file open,
a transient permission error). `None != <hash>` is `True`, so a live file that could not be
*read* is reported to the operator identically to one whose *content* actually differs. This
directly contradicts `digest()`'s own docstring, which says the None-vs-hash distinction "must
be distinguishable from a file that hashed to something, which is why the caller checks for
None explicitly" — true of `snapshot()`'s `missing = [... if d is None]` a hundred lines above,
untrue of `verify()`'s `changed`/`added`/`gone`, none of which ever test `d is None`.

Lower stakes than a write-path bug — `verify()` is read-only diagnostics over an already-landed
backup, not the backup itself — but it can misreport a routine file lock as data drift, on the
read side of the exact discipline ("a backup that was never read is a belief, not a backup")
this module's whole docstring is built around.

### 1.5 `c54bb7d84622` — MINOR / LOCAL — `feats.resolve_title()` and `_page_exists()` are unmarked dead code

Zero callers anywhere in the repository (grepped the whole tree, not only `src/`) for either
`resolve_title` or `_page_exists`. `resolve_title()` in particular carries a substantial,
carefully-argued docstring about safely ranking wiki-title candidates ("17,148 entries mined to
nothing because the entity's catalogue name is not the wiki's page title") — it reads as active
machinery that closed a measured, real problem, but nothing calls it, so that problem is still
open in every code path that actually runs. This module's own house doctrine (order
`25ec11447b4c`, applied three hundred lines later to `axis_evidence`) requires dead code to be
*reported* dead rather than silently unmarked; these two functions carry no such marker.

---

## 2. Notable non-findings — read carefully, not filed

**`feats.mine()`'s `gate_rejected` is a narrower list than the module's opening claim.** The
docstring promises the miner "keeps everything it gathers, including what the gate turned
down." In fact `mine()` only records a rejected sentence when it also matches `_QUANTITY` or a
destroy/obliterate/shatter/survive regex — a sentence that fails `valid_scale_note` and matches
neither is dropped with no counter of its own. Read this as likely-deliberate rather than filing
it: the full cleaned page text is separately retained verbatim in `evidence_for()`'s `text`
field, which is arguably the actual referent of "everything it gathers." Flagged here as a
question rather than an order because the alternate reading (deliberate near-miss curation, not
a promise about every discarded sentence) is at least as plausible as the defect reading.

**`custodes.py`, `retry_synthesis.py`, `wh40k.py`, `policy.py`** were read in full and are
already extensively self-audited — every live risk I could find in them traces to an order
already open in `state/workorders.json` (`bd673ceaaf31`, `00a85c511b53`, both correctly still
open) or already closed with a verified fix in `state/workorders_closed.jsonl`. No new findings.

**`custodes._transit_widening()`**: if a second Custos were ever flagged `dispersive=True` with
`dof="currency"` alongside Lumen, the widening would be summed additively from the *same*
`distance`/`years_since` pair for both — a latent double-count. Not filed: only Lumen carries
that flag today, this is speculative about a table entry that does not exist, and the module's
own comments already anticipate and document this general class of future-proofing gap for
adjacent cases (the zero-tilt/nonzero-sensitivity coupling, `table_faults()`).

---

## 3. Coverage recorded

```
python -c "import sys;sys.path.insert(0,'src');import sweep_plan;sweep_plan.record('run46',['feats.py','corpus_db.py','custodes.py','policy.py','canon_backup.py','retry_synthesis.py','wh40k.py','descending_ladder.py'],batch=7)"
```
