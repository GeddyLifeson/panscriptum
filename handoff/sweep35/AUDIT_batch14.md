# sweep35 batch14 audit

Modules: src/hostcheck.py, src/workorders.py, src/chain.py, src/custodes.py, src/policy.py,
src/axis_correlation.py, src/tells.py, src/physics.py (3,579 lines). Read in full, offset-paged.
No edits made under src/. Verified every candidate against source and against the open/closed
queue before filing (`state/workorders.json`, `state/workorders_closed.jsonl`) to avoid
re-filing what other batches already caught.

## Filed (4)

1. **ebecc3cc19a7** — `workorders.py:523-545` — `_supersede_binding_suspect()` only ever closes
   the old `BINDING_SUSPECT` code, never the sibling *decided* code. If binding_health's identity
   verdict for a host flips between `CONFIRMED` and `MISBOUND` across sweeps, the newly-filed
   order supersedes `BINDING_SUSPECT` but the previous decided-code order
   (`BINDING_RIGHT_ENTRY_NAMES_ARE_NOT_TITLES` or `BINDING_HOST_SERVES_ANOTHER_WIKI`) has no
   closing path — the recovery loop at 559-571 only fires on `healthy is True`, not on a verdict
   change while `healthy` stays `None`. Two contradictory OWNER-rung orders can stand open for
   the same host indefinitely.

2. **53a0111dccac** — `hostcheck.py:396-425` — `null_rate()` collapses a genuine probe *failure*
   (network error, throttling, or an empty foreign-name sample) into `baseline = 0.0` — the exact
   conflation `probe()` itself was fixed to stop making (its own comment at line 152 says a
   failed request is "NOT a rate of zero"). Because `score()`'s `lift = rate - base` and
   `null_rate()` is cached per host for the process lifetime, one throttled control probe
   silently inflates lift (and therefore the `holds`/`partial`/`WRONG FICTION` verdict) for every
   source scored against that host for the rest of the run.

3. **2af7ca515157** — `custodes.py` — Lumen's entire reason for existing (dof=`currency`,
   staleness/lightcone dispersion) never fires in production. `staleness_widening()` returns 0.0
   whenever `distance` or `years_since` is `None`; `convene()` defaults both to `None`; and no
   caller anywhere in the tree (`anchors.py`, `verify_math.py`) ever supplies real values. Her
   `dispersive=True` flag is set and commented but never read anywhere. The published interval's
   currency/staleness degree of freedom is manned on paper only.

4. **9ef866225683** — `policy.py:43-44,140` — `evaluate()`'s vacuous-pass detector flags every
   rule using `op="absent"` as vacuous the instant it correctly passes, since a correct
   absence-check's only honest pass *is* `found=False`. No live rule table uses `absent` yet, so
   nothing misfires today, but the module's stated purpose (telling a real pass from a vacuous
   one) is defeated for that op by construction.

## Checked, already covered by other batches (not re-filed)

- `tells.py:81-82` "it's not X, it's Y" / "X is not Y; it is Z" cannot match the contracted forms
  they are named for — already open as **faee3befb768** (SWEEP34, batch8). Independently
  re-derived and confirmed identical before standing down.
- `physics.py` `binding_energy()` losing the sign of a negative mass via squaring — already open
  as **adffa670486c** (PHYSICS_NEGATIVE_MASS_UNCHECKED).
- `axis_correlation.py` — four separate live findings already open (rho() 0.0-fallback framing,
  `main()` TypeError on `mean_r=None`, `observations()` silently skipping a missing source file,
  header prose mismatch). The "217 automated assays contribute nothing to the matrix" gap the
  module's own docstring flags as filed was verified: it was filed and already **closed**
  (`b03f2ab9951a`) as fixed.
- `allsweep.py`/`workorders.py:130-172` ESTATE-tier exclusion from the graded verdict — already
  open as **5863bd9f566a**.

## Read and cleared (no new finding)

`workorders.py` CAS write path (`_mutate`/`file_order`/`resolve`), the handler-ladder validation,
`sweep_detectors()`'s per-section detector-failure wrapper and the three `file_order` results in
the binding-identity section (already fixed to be counted, verified by reading), `open_orders`/
`for_ladder`/CLI printing (no caps found). `chain.py` harvest incrementality, dedup key, mutual-pair
epoch adjudication, `write_result` schema. `custodes.py` DoF/Custos table, `convene()`'s interval
math and Threnody veto (the `covers_every_reading` tautology is self-documented in the code as
intentional, not a surprise). `policy.py` limit/scope reporting (already fixed pre-sweep35).
`hostcheck.py` `candidates()`, `roster_audit()`, `purge()`, `adopt()` for caps/truncation —
none found; all use full unbounded lists per Hard Rule 0.
