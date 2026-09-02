# Sweep 41 — Batch 09 audit

Modules read in full: `src/foreman.py` (1,745 lines), `src/allsweep.py` (876), `src/rosetta.py`
(640), `src/handbuilt.py` (516), `src/backfill.py` (411), `src/navtree.py` (335),
`src/entity_match.py` (296), `src/halo.py` (219). Total 5,038 lines, matches the batch brief
exactly.

General note: every one of these eight files carries extensive inline "here is the bug we found
and fixed, and why" commentary from prior runs (23 through 40), and this batch is a re-verification
pass more than a fresh discovery pass. Confirmed today's stated fixes are actually in the source:
`foreman.kill_stalled_job`'s fail-closed absent-row split (`foreman.py:540-545`), `restart_ollama`
reporting real elapsed time (`foreman.py:1082`), `rosetta.assays_by_host`'s `partition("|")` fix
(`rosetta.py:320-330`), and `backfill`'s `not_fetched`/`dropped_as_stub` reporting
(`backfill.py:233-308`) — none of these are re-reported below.

One new finding was filed. It was independently narrated in `handoff/sweep23/AUDIT_batch03.md`
eighteen runs ago but never actually turned into a work order (`state/workorders.json` has zero
hits for `reprove_pool`) — the code is unchanged since then, so it is still live and is filed now.

---

## Filed

### FOREMAN_REPROVE_POOL_BREAK_SKIPS_RESTART_READER — MAJOR — OWNER — id `7ad10a229440`

`src/foreman.py:1109` (REMEDIES), `:177-212` (`reprove_pool`), `:1614-1627` (the break in
`round_once`).

`REMEDIES["the library's counters are moving"] = [reprove_pool, restart_reader]`. The dispatch
loop breaks the remedy list the first time one returns `did=True`, unless the remedy carries a
`.always` mark — and only `run_completeness_audit` and `refresh_coverage` carry that mark today.
`reprove_pool` returns `True, f"{len(ok)} of {len(rows)} buckets answer"` whenever `CB.prove()`
runs and the write lands, **regardless of `len(ok)`** — even 0 of N buckets answering counts as
`did=True`. So under this standard, `reprove_pool` runs first, almost always returns `True` (only
a write denial or an exception makes it `False`), the break fires, and `restart_reader` — the
second remedy in the list — never runs.

`restart_reader`'s own docstring names the exact incident this standard exists to catch: "the
counters-flat stall it serves is precisely the case where the reader is alive, logging failures,
and doing nothing" — a condition the pool-health re-measurement cannot detect or fix. A healthy,
freshly-reproved pool sitting beside a wedged-but-alive reader is exactly the shape that both (a)
leaves the standard breached and (b) guarantees, by construction, that the one remedy able to
address it is skipped.

This is the identical class of bug the module already fixed once, in the same file, for a
different pair: `run_catalogue_gap` returning `True` used to skip `run_completeness_audit`
entirely, which is why the audit was given `.always` — "measuring is not an alternative to
repairing" (`foreman.py:1611-1613`). `reprove_pool` measuring successfully is not the same claim
as the counters having resumed, for the same reason.

Filed as a question rather than a certain finding because a defensible Reading B exists (see the
order text): the two remedies could be deliberate graduated response, cheap re-measurement before
an expensive kill with a documented 42-44-minute-to-4-hour restart horizon on this job
(`FOREMAN_RESTART_READER_UNRESTARTABLE`, `d2e44a766769`, still open, covers a *different* gap on
the same remedy — `restart_reader`'s own missing `_restartable()` gate — and does not mention this
dispatch-ordering issue). Reading A treats it as the same omission the `.always` fix was meant to
close and missed.

---

## Verified clean / already fixed, not re-filed

- **`foreman.kill_stalled_job`** (`:540-545`) — the absent-standard-row vs. measured-and-holds
  split is in place exactly as today's context describes. `state/workorders.json` still carries
  the open order `FOREMAN_STALL_UNMEASURED_REPORTS_NO_STALL` describing the *old* code (`if not
  row or row.get("holds"): return True`) — that text no longer matches the source. Not re-filed
  (nothing to file — the code is already right); flagging here only because the open-order queue
  itself is stale and someone should resolve that ticket, which is outside this audit's remit
  (audit, not repair, and I don't own the ruling).
- **`restart_ollama`** (`:1015-1086`) — the 30-minute stamp fails closed on an unreadable file
  and reports genuine elapsed seconds on a failed respawn wait.
- **`rosetta.assays_by_host`** (`:306-331`) — `partition("|")` only splits when the separator is
  actually present; a bare key files under the empty host with its name intact, matching the
  docstring.
- **`allsweep.py`** — all five tiers (IMPORT/LINT/VERIFY/ESTATE/RECONCILE) are honestly separated:
  `bad` sums only graded tiers, RECONCILE is deliberately excluded and the exit code / console
  both say so (`:819-826`), `estate_faults` fail-closes on a missing `bad` key (`:574-583`), and
  the halt-refusal special case (`A SAFETY THAT STOPS WORK IS NOT A FAULT THAT STOPS WORK`) is
  applied identically in both the IMPORT tier and the VERIFY tier. No new defect found.
- **`handbuilt.py`** — matches the sweep38-batch04 finding that `compute()` is correct, the
  `"unestimable"` sentinel is guarded by `isinstance` before formatting (`:495-496`), and the
  write lands (via `silence.write_json`) before anything is printed, closing the console-encoding
  race the module's own comment describes.
- **`backfill.py`** — the `t in sizes` ranking key (ascending, unmeasured sorts with the deepest
  articles rather than last), the pre-cap `absent` count, and the `not_fetched`/
  `dropped_as_stub`/`size_lookup_failed` triple are all present and all summed into `--all`'s
  closing report, matching the module's own extensive comments about the failure modes each one
  replaced.
- **`navtree.py`** — the register/grounding-type tie-breaks are deterministic (secondary sort on
  name, per the m41 comment), the `sources_under` prefix match requires `"."`-bounded segments on
  both arms (BUGS m11), and `main()`'s exit code now reflects a denied audit-record write or an
  unclean audit on a read-only run, not just `--write`'s own path.
- **`entity_match.py`** — `qualifier_compatible` is the absolute gate the module promises (a
  qualifier conflict is never overruled by similarity), `candidates()` returns one consistent
  shape on every path (no `KeyError` on an empty name or empty pool), and sort order is
  deterministic (score desc, name asc — never hash order). Confirmed still uncalled by any
  production module (`grep -rl "import entity_match" src/` → only `verify_math.py`, which is the
  module's own stated state, not a regression). No new defect found; this file has now been
  independently re-verified clean across roughly a dozen prior sweeps (22 through 37) and this one.
- **`halo.py`** — small, fully hand-curated, three-entity roster; provenance is per-axis (`wiki`
  vs `canon`), the write is gated and reports a denial honestly, and `--full`'s citation wrapping
  is unclipped. No defect found.

## Decided NOT to file, and why

- The `reprove_pool`/`restart_reader` finding above was the only thing surfaced this batch that
  both (a) is real and verified against current source and (b) was not already an open work
  order. Everything else that looked like a candidate on first read (rosetta's `check()` stamping
  `ambiguous_assay_names` from the unscoped map even on the scoped path; rosetta's CLI-only
  `[:12]`/`[:6]` console caps; `restart_reader`'s missing `_restartable()` gate) turned out to be
  either already open (`FOREMAN_RESTART_READER_UNRESTARTABLE`, `ROSETTA_CLI_CAPS`,
  `ROSETTA_PROBE_ERRORS`) or already recorded as a deliberate not-filed observation with reasoning
  that still holds (`ambiguous_assay_names`, recorded in sweep38/sweep39, no live consumer reads
  the field) — re-filing either would be queue churn per the standing instruction against that.
- `navtree.py`'s `src`-count accumulation across tiers is not cross-checked by `audit()` the way
  the world (`n`) count is (`audit()` only verifies `n` against children/`w`). This is a real gap
  in the audit's coverage but not a demonstrated defect — `src` is accumulated by the exact same
  mechanism as `n` (no separate merge step to introduce drift), so there is no live symptom to
  point at, only an unaudited invariant. Not filed for lack of a concrete failure; worth a second
  look if `navtree`'s source counts are ever seen to disagree with reality.
