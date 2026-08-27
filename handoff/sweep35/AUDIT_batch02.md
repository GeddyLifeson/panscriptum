# SWEEP35 batch02 — audit of src/drill.py (4347 lines, read in full)

Scope: single module, src/drill.py, the attack-suite battery. Read offset-by-offset from line 1
to 4347, no sampling. Checked existing state/workorders.json first (grep for "drill.py" and the
SWEEP34_BATCH03_LINE_NUMBERS_SHIFTED note) to avoid re-filing known issues.

## Overall impression

This is an unusually self-aware file: most of its ~250 nets carry docstrings narrating a real
past defeat (an "AUDIT DEFEAT", a run-numbered incident, or a prior sweep finding) and the fix
that followed, including several instances where the file explicitly rewrote a check from a
literal source-substring scan to an AST-based call-graph check *because* the substring version
was satisfied by a comment. That history made the remaining live weaknesses easier to find: they
are the same class of defect the file's own docstrings warn about, just not yet swept up.

## Findings filed (3)

1. **MAJOR — `abandoned_sandboxes_are_reaped` cannot go red** (drill.py:3831-3841). It calls
   `M.reap_orphans(older_than=10**9)` and asserts `== []`. Since `cutoff = now - older_than`, a
   threshold of ~31.7 years means nothing on the filesystem can ever be old enough to be reaped,
   so the call returns `[]` regardless of whether `reap_orphans` works at all. Gutting
   `reap_orphans` to `return []` unconditionally — the exact 154MB-leak regression this net
   exists to catch — leaves it green forever. The net never creates a genuinely aged orphan
   sandbox and confirms it gets deleted.

2. **MAJOR — a recurring "wired-where-claimed" class still uses whole-file literal-substring
   checks**, the same failure this file already fixed three times elsewhere
   (`_no_programmatic_clear`, `_withdrawal_takes_a_snapshot`, `guards_are_wired_where_claimed`),
   with the docstring lesson "a literal cannot tell code from prose about code." At least nine
   live instances remain unfixed, two added TODAY in `drill_binding_identity`. Filed with
   file:line verification for each and a concrete defeat (a comment or dead branch reproducing
   the searched string while the real call is deleted or the real condition is loosened).

3. **MINOR — `index_query_cannot_write` (drill.py:4142-4163) operates on the live corpus_db.DB**,
   not a scratch copy. If the guard under test is actually broken, the CREATE TABLE lands for
   real; the cleanup attempt can itself fail silently (`silence.note` only), leaving a stray
   table in the live SQL index. Lower severity because the failure path already raises
   DRILL_BREACH and pages a person, but it contradicts the file's own "never writes to the
   corpus" framing.

## Areas specifically re-checked because they were flagged as added today

`drill_binding_identity` (binding identity + roll `rows=` trap + mutation sandbox target check +
network-memo net) was read in full and driven line by line against the real functions it calls
(`binding_health.py`, `roll.py`, `mutate.py`, `standards.py`). `_rows_kwarg_does_not_write_the_
real_roll`, `_sandbox_without_its_target_refuses`, and `_battery_asks_the_network_once` all call
the real guarded function, redirect only the module-level path/state needed for isolation, and
assert on real before/after state — no defects found there. The two weaker nets in that same
function (the two source-substring checks) are covered in finding #2 above.

Probe-litter cleanup (`_sweep_probe_litter`, `a_probe_leaves_no_order_behind`,
`blast_cap_bites`, `area_fault_does_not_close_the_park`) was checked for the "record don't
swallow" discipline the file claims for itself — each cleanup failure path does call
`silence.note` rather than a bare `pass`; no new litter-producing probe found beyond what is
already in finding #3.

## Not filed (considered and rejected)

- `breached[:5]` display truncation in `main()` (drill.py:4322, 4328): the printed/escalated
  *names* list is capped at 5, but the printed *count* (`len(breached)`) is always accurate and
  the full list is preserved in the escalation's `evidence` dict — not the Hard-Rule-0 shape
  (a report that hides a smaller universe), just a display convenience. Skipped.
- `excluded_sources_keep_their_records`'s bare `except Exception: continue` while scanning
  records (drill.py:3954): only affects an existence check used defensively, not a completeness
  claim like `_policy_corpus_clean`'s. Skipped as not load-bearing.

## Coverage recorded

`sweep_plan.record('run35', ['drill.py'], batch=2)` — done.
