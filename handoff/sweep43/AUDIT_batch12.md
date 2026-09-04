# Sweep43 batch12 audit — workorders.py, health.py, custodes.py, codewatch.py, policy.py, hosts.py, physics.py, tuning.py

All eight files read completely, top to bottom, from the current on-disk source (not from memory
of any prior pass). Two defects the brief said were already fixed this shift in `workorders.py`
(`_fire`'s inverted arms; `--handler` unread plus the uncapped 70-char queue listing) were checked
against the current file and are confirmed fixed — not re-filed.

This batch is unusually heavily self-audited already: the majority of the code carries inline
"order NNNN" comments documenting a defect that was already found and fixed in a previous shift,
with the reasoning preserved. I verified a representative sample of those against the live logic
(not just the comment) rather than taking the comment's word for it, and did not find any of them
still live. The findings below are new: things the existing comments do not already name.

## workorders.py

Clean on this pass, beyond the two pre-fixed defects named in the brief. `_fire`, `_mutate`'s
compare-and-swap, `resolve`'s land-then-exist ordering, `ghost_orders`' time-separation logic,
`_supersede_binding_suspect`'s sibling-code closing, and `cap_boundary_scan` were each traced
against the current source and behave as documented. No new finding.

## health.py

Clean of new correctness/safety defects. One MINOR, filed below: `check_caches()`'s `< 25` file
threshold that exempts small cache directories from the "all-empty" broken-cache detector has no
justifying comment, which is conspicuous in a module where every other threshold in this file
carries one.

- MINOR — `src/health.py:591` — `if len(files) < 25: continue` — A host directory holding fewer
  than 25 cached entries is skipped entirely by the "systematically empty" detector, so a small,
  newly-added host that is 404ing on every request (the exact failure class this module exists to
  catch — see the docstring's Wikipedia example) produces no finding until it accumulates 25
  cache files. Every other numeric threshold in this file (`EMPTY_BYTES`, `PROOF_STALE_SECONDS`
  equivalents elsewhere, the `25` itself in spirit) is accompanied by a comment defending the
  number; this one is not, which is the anomaly worth surfacing rather than a proven bug. It may
  be a deliberate statistical-significance floor. Filed as a judgment call for OWNER: either add
  the justification, or lower/remove the floor so a small broken host is not permanently invisible
  to this check.

## custodes.py

Clean. `table_faults()`'s zero-tilt/nonzero-sensitivity check, the abstention wiring for Threnody
(`eta`) and Lumen (`distance`/`years_since`), the `_transit_widening` dispersive-flag consultation,
and `convene()`'s attendance-before-early-return ordering were each traced and match their
docstrings. Ten Custodes, ten degrees of freedom, `dof_coverage()`'s `one_to_one` check is correct
by inspection of the table.

## codewatch.py

Clean of new findings. Every mechanism (`fingerprint`, `quiet_seconds`'s wall-clock settle window,
`runs_script`'s synthetic-argv matching, `twins`'s self-exclusion, `_ledger_lock`'s stale-lock
theft, `_take_locked`'s fail-closed-on-denied-write, `stale()`'s mtime-vs-poll corroboration) was
traced against its docstring and is correct. See the Questions section below for a design tension
worth flagging to the owner rather than filing as a fault — the code already argues its own case.

## policy.py

Clean. `OPS`/`TYPES` closed-set refusal, the `absent`-operator exemption from the vacuous-pass
check, `_observed`'s bounded-but-marked repr, and `main()`'s scope/partial-run bookkeeping were
each traced and match. No new finding.

## hosts.py

Two MAJOR findings — both are the same class of defect this whole batch is watching for: "no
data" rendered indistinguishable from "clean."

- MAJOR — `src/hosts.py:44-50` — `_load()`:
  ```python
  def _load(path, default):
      try:
          with open(path, encoding="utf-8") as f:
              return json.load(f)
      except Exception:
          silence.note("hosts.py:load")
          return default
  ```
  This is the sole reader for both `data/WIKI_HOSTS.json` (`PRIMARY`) and `data/SOURCE_HOSTS.json`
  (`EXTRA`), used by `primary_host()`, `hosts_for()`, `discover()`, and `coverage()`. It does not
  distinguish "file absent" (honestly empty — a fresh clone) from "file exists but is corrupt or
  unreadable" (a torn write, a lock, a permission error) — both collapse to the caller's `default`
  (`{}`), with only a `silence.note` class-name counter bumped, which `health.py`'s own docstring
  describes as landing nowhere on the handler ladder. This is the exact hazard `workorders.py:_load`
  was hardened against (three states, not two — see its docstring) and the exact hazard
  `hostcheck._land_hosts`, the WRITER of this very file, already refuses to heal for
  (`src/hostcheck.py:152`, "NEVER heal this one by starting empty... it is not reconstructible;
  fix the file") — `WIKI_HOSTS.json` is named there as one of two files in the project confirmed
  not reconstructible from anything else. `hosts.py`'s reader does not carry the same discipline
  the writer for the identical file already has. Concretely, a corrupted `WIKI_HOSTS.json` makes
  `coverage()` report `sources: 0` (a plausible, clean-looking number) instead of an error, and
  makes `discover()`'s `todo` list empty, so a `--discover` run walks nothing, prints "hosts added:
  0", and exits 0 — reading exactly like "nothing new to find" rather than "the host registry could
  not be read." Verified by inspection of every call site of `_load`; no call site distinguishes
  the two cases. Note on blast radius: no other module in `src/` currently imports `hosts.py` in
  production (`grep` found only a comment reference in `hostcheck.py`), so today this only affects
  the `hosts.py` CLI itself (`--discover`, `--show`, `--stats`) — still worth fixing before anything
  starts depending on it, and consistent with this batch's brief that instrumentation defects are
  worse than they look because nothing else can see them either. Remedy: give `_load` the same
  three-state treatment `workorders.py:_load` uses — `FileNotFoundError` alone means absent
  (return `default`); any other exception means UNREADABLE and must be surfaced (raise, or return
  a sentinel every caller checks) rather than silently returned as `default`.

- MAJOR — `src/hosts.py:177-181` — inside `discover()`'s `work()` closure:
  ```python
  try:
      grounded, spec = HC.candidates_split(source, cur, by=by, hosts=prim)
  except Exception:
      silence.note("hosts.py:candidates")
      return None
  ```
  and the consuming loop in `discover()`:
  ```python
  for res in ex.map(work, todo):
      if not res:
          continue
      source, keep, withheld = res
  ```
  When `HC.candidates_split` raises, `work()` returns bare `None`, and the consumer's `if not res:
  continue` drops it with no further trace — the source is not added to `not_probed` (the
  thin-roster list, printed and counted), not added to `lost` (denied-write list, printed and
  escalated), and not reflected in `withheld_total`. It simply disappears from every number
  `discover()` prints. This is the identical shape to a defect this same function already fixed
  four lines above it (`len(names) < 4` -> `return (source, None, 0)`, order f28f27da7c1f, whose
  own comment states the principle: "a bare `None`... reads the same way whether the source was
  probed and held nothing or was never probed at all... an unstated bound is indistinguishable
  from no bound at all"). The fix was applied to the thin-roster case and not to this one, which
  sits right next to it. A source whose candidate generation throws (a real possibility —
  `HC.candidates_split` walks `by`/`hosts` structures built from live scan data) is silently
  omitted from a `--discover` run's summary with nothing but an unread failure-ledger counter to
  show it happened. Remedy: return a distinguishable sentinel (e.g. `(source, "error", str(exc))`)
  and have `discover()` collect and print/count these the same way it already does for
  `not_probed` and `lost`.

## physics.py

Clean. Every guard function (`kinetic`, `joules_for`, `sphere_volume`, `binding_energy`) refuses
non-positive/non-finite inputs and non-finite results consistently; traced the NaN/inf edge cases
by hand against each guard's stated purpose and found no gap (e.g. `kinetic`'s `v >= 0.0` check
correctly catches NaN via the universal-False-comparison property, ahead of the `v >= C` check).

## tuning.py

Clean. `regime()`'s cloud/local/starved decision tree, the `judged` gate on `MIN_CALLS_TO_JUDGE`,
`profile()`'s buckets-cached-alongside-verdict fix, and `workers()`'s zero-is-a-request fix were
each traced and match their docstrings.

## Questions (for OWNER, not filed as findings — both sides are defensible)

1. **codewatch.py's `runs_script`/`twins`/`claim_singleton` deliberately FAIL OPEN**
   (`src/codewatch.py:194-196`, `:272-275`): when a command line's script path is relative and the
   process's cwd cannot be read, or when `psutil` is unavailable, this module treats "cannot tell
   whether a twin is running" as "no twin is running" and lets a second daemon start — reasoned
   explicitly in the docstring as the lesser evil ("an outage that reports itself as caution is the
   worst shape a safety can take"). CLAUDE.md's Hard Rule -1 states every layer in the project must
   answer "I don't know" with STOP and calls silence-authorising-anything the failure this project
   keeps re-finding. This is a considered, argued exception to that doctrine rather than an
   oversight — worth a ruling on whether twin-detection is meant to be exempt from FAIL CLOSED, or
   whether it should be tightened now that `codewatch.py` and `escalation.py` exist to make a
   refusal cheap and visible rather than a bare outage.

2. Not a question about this batch's code, but a scope note: `state/cascade_scratch.db`, which
   `tuning.cloud_success_rate()` reads, was confirmed present and readable during this pass — no
   new finding there; the brief's note that it was "missing from the mutation sandbox and has just
   been fixed" was not re-checked further since it was named as a known, already-resolved
   condition.
