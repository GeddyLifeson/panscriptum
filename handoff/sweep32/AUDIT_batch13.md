# AUDIT batch13 — run32

Modules read in full, every line:

| module | lines |
|---|---|
| src/assay.py | 868 |
| src/derivation.py | 558 |
| src/custodes.py | 418 |
| src/ingest_doc.py | 302 |
| src/hosts.py | 253 |
| src/style_audit.py | 211 |
| src/repass_bands.py | 119 |
| src/lognames.py | 36 |

Cross-referenced (not full-line-audited, read only as needed to trace callers): `dashboard.py`
(lines ~480-520, ~907-960), `anchors.py` (~160-220), `pipeline.py` (`write_record`,
`write_record_catalogue`, `_landed`), `silence.py` (`write_json`, `replace_retry`).

---

## BLOCKING

**assay.py:496-531 (`calibration_report`) x dashboard.py:514,907-960 — unsynchronized global
mutation of `SIGMA_BY_ATTESTATION` under a threading server; can permanently corrupt the
constant, not just transiently.** VERIFIED.

`calibration_report()` sweeps `SIGMA_BY_ATTESTATION["Witnessed"]` through ~800 values
(`0.005` step over a `±2.0` window, assay.py:513-521), calling `assay()` at each step, then
restores the saved value in a `finally` (line 522-523). No `threading.Lock` exists anywhere in
`assay.py`, `dashboard.py`, or `silence.py` (grepped — zero hits). `dashboard.py:924` runs
`class Server(socketserver.ThreadingTCPServer)` with `daemon_threads = True`, and
`Handler.do_GET` (line 907) calls `state()` → `_AS.calibration_report()` (line 514) on every
`GET /api/state` — which the dashboard's own comment says is polled every 5 seconds
(`log_message`, line 917-919), and which fires once per concurrent request (two browser tabs, a
slow first request plus a retry, etc.).

Two concurrent `/api/state` requests run `calibration_report()` in two threads simultaneously.
Effects, worst first:
1. **Permanent corruption, not just a transient race.** Thread A's `saved = SIGMA_BY_ATTESTATION["Witnessed"]`
   (line 512) can capture a value B has already mutated mid-sweep. When A's `finally` restores
   "the original", it writes back a value that was never the true calibrated constant
   (`3.2003`, the charter-derived anchor at line 375). The process now serves a wrong sigma for
   `attestation="Witnessed"` for its entire remaining lifetime — silently, no exception, no log.
2. **Transient corruption of every concurrent `assay()` call.** Any other thread computing a
   real entry's Magnitude with `attestation="Witnessed"` during the ~800-iteration sweep window
   gets an interval computed from whatever sigma the sweep happened to be testing at that
   instant, not the calibrated one.
`SIGMA_BY_ATTESTATION` is the constant every printed `𝔄 M#.## ± #.##` in the library is built
from (assay.py's own docstring, lines 413-416: "a calibration that drifts is a library-wide
falsehood, and it is the QUIET kind"). This is exactly the failure class the file's own
"SAFETY NETS" section (assay.py:408-426) claims to defend against via independence/fail-closed/
proven — none of which cover concurrent mutation, because none of the four listed mechanisms is
a lock.

Concrete failure scenario: run `dashboard.py`, open two browser tabs (or let one slow poll
overlap the next 5s tick), watch `SIGMA_BY_ATTESTATION["Witnessed"]` — it can settle on a value
other than 3.2003 and stay there.

---

## MAJOR

- **custodes.py:267, 290-357 — Threnody's `veto` field is computed and never read; the only
  production caller never supplies the `eta` the real veto gates on, so nothing in the shipped
  pipeline ever refuses an Assay.** VERIFIED.
  `_custos_reading()` (line 237) returns `"veto": bool(c.get("veto"))` per Custos (line 267) —
  `True` only for Threnody (`veto=True`, line 183). `convene()` (line 290) collects all ten
  readings into `vals = [r["reading"] for r in readings]` (line 306) and averages/dispersion-
  computes over all of them uniformly (lines 309-320) — `r["veto"]` is never inspected anywhere
  in `convene()`. Threnody's numeric `reading` is blended into the consensus exactly like every
  other Custos's; her `veto=True` flag is dead data.
  The actual refusal path is a *different*, unrelated mechanism: `if eta is not None and
  (1.0 - eta) >= CURL_VETO_THRESHOLD:` (line 352), gated on an `eta` parameter that has nothing
  to do with Threnody's own computed reading. `grep`-traced every caller of `convene(`: the sole
  production caller is `anchors.py:190`, `col = CU.convene(a["anchor"], a["scores"],
  attestation=a["attestation"], worksheet="anchors.py")` — no `eta=` argument, so it defaults to
  `None` and the veto branch is unreachable. The only calls that ever supply `eta` are
  `custodes.py`'s own `main()` demo (line 410) and `verify_math.py`'s self-tests. The docstring
  at custodes.py:178 ("Hers is the only standpoint that can refuse the output rather than shift
  it") is directly contradicted by the code: her reading shifts the output like everyone else's,
  and the thing that actually refuses output is unconnected to her.
  Consequence for Hard Rule 3 (no rubber-stamped Assay): an entity whose contest structure is
  substantially non-transitive (curl-heavy, no faithful scalar per the charter's own Theorem 1)
  gets a scored composite from `anchors.py`'s call path anyway, because the one standpoint
  charged with catching that case is wired to a parameter nobody supplies.

- **ingest_doc.py:293 — `P.write_record(rp, rec)` return value discarded; a denied write is
  completely silent, with the same module documenting the exact opposite discipline 60 lines
  away.** VERIFIED.
  `pipeline.write_record()` returns a bool (`_landed(...)`, pipeline.py:465,567) and explicitly
  does **not** raise on a denied replace — `silence.replace_retry`'s own docstring: "persistent
  denial is recorded, never raised." ingest_doc.py:290-293 calls it and ignores the return:
  ```
  if "ingest_doc" not in (rec.get("provenance") or ""):
      rec["provenance"] = (rec.get("provenance") or "") + note
      import pipeline as P
      P.write_record(rp, rec)
  ```
  wrapped in `try/except Exception: silence.note(...)` (line 294-295) — which cannot catch this,
  because a denied write does not raise. If the record file is held open by a concurrent reader
  (documented elsewhere in this same project as a routine Windows occurrence — `silence.py:264-268`),
  the provenance note is silently never written, with zero trace: no exception, no `silence.note`
  call from this call site, no retry. This is precisely the bug class `mine()` in the *same
  file* goes out of its way to describe and avoid at lines 233-251 ("ADVANCE ON THE WRITE, NOT
  ON THE INTENT... discarding the result advanced the resume cursor past entities that were
  never saved") and the same class `repass_bands.py:78-87` (a sibling module in this batch)
  explicitly gates on ("GATE ON THE WRITE... the script still reported it as rewritten (run
  #25)"). The `--pdf` code path is the one place in ingest_doc.py that regressed to the
  discard-the-return-value pattern.
  Severity note: provenance text isn't a scoring input, so this doesn't corrupt an Assay
  decimal — but it is a genuine silent data-loss bug in a shared-record write path, in a file
  that otherwise treats this exact failure mode as serious enough to document at length twice.

- **hosts.py — `discover()`'s `add()` calls race across `ThreadPoolExecutor(max_workers=workers)`
  threads (default 6) on the shared file `SOURCE_HOSTS.json`, a classic lost-update.**
  VERIFIED mechanism, SUSPECTED to actually lose data at the stated worker count.
  `add()` (line 78-97) does a full read (`_load(EXTRA, {})`, line 82) of the whole
  `SOURCE_HOSTS.json`, mutates only its own source's entry, then does a full atomic overwrite
  via `silence.write_json` (line 94). `silence.write_json`/`replace_retry` guarantee the
  *write itself* lands intact (unique-per-pid/thread tmp name, atomic rename) but provide no
  cross-caller locking or merge — confirmed by reading `silence.py:290-327`, which documents
  atomicity but not serialization. `discover()` (line 125) drives this via
  `ThreadPoolExecutor(max_workers=workers)` (line 190, default `workers=6`) with `work(source)`
  running once per source in whatever thread the pool assigns, and `work()` calls `add()` once
  per kept host (line 195-197). Two threads processing two different sources whose `add()` calls
  overlap will both read the file before either writes; the second writer's full-file overwrite
  discards the first writer's addition with no error, no note, no indication anything was lost —
  it looks like ordinary progress. This is the same shared-state hazard class explicitly named
  in the batch brief (item 4) and the one `silence.write_json`'s own docstring was written to
  document (elsewhere in this project, at a different call site) — but the docstring's fix
  covers write-vs-write file corruption, not the read-modify-write race one level up in the
  caller, which nothing in `hosts.py` guards against (no lock, no CAS, no re-read-before-write
  in `add()`).

---

## MINOR

- **assay.py:219-223 (`axis_score`) — flat `9.9` for every M10 input, confirmed by arithmetic;
  self-documented as open bug M18, still unfixed.** VERIFIED, but pre-tracked (found in
  `BUGS.md`, `NEXT_STEPS.md`, and prior sweep audits — not new).
  `LADDER` has 11 entries (M0..M10, indices 0-10). For `band="M10"`, `i = LADDER.index(band) = 10`;
  `i + 1 = 11 >= len(LADDER) == 11` is `True`, so the function returns the literal `9.9`
  regardless of `x` (any positive value) before ever looking at `BAND_EDGES`. Two M10 entities
  with wildly different attested feats — one barely above the M10 floor, one far beyond — score
  identically on every axis. Because `axis_score` saturates below `AXIS_MAX = 10.0`
  (deliberately, per the comment at lines 313-320), an M10 entity's composite can never actually
  reach the `_dec >= 1.0` ceiling/promotion check (assay.py:650) through this path, since every
  scored axis tops out at 9.9/10. Confirmed still open: `grep -rl M18` hits `BUGS.md`,
  `HANDOFF.md`, `NEXT_STEPS.md`, and prior sweeps' audit files, so this is known and tracked
  rather than a new discovery — flagged per instructions to confirm/refute the lead, and
  refuted only in the sense that it's not silently hidden: the comment at assay.py:313-320
  names it explicitly as "its own open bug, M18."

- **custodes.py:335-344 (`covers_every_reading`) — a tautology, self-documented as one.**
  VERIFIED, self-acknowledged in-code (lens item 7, "checks that cannot fail").
  `half = max(1.96 * total_sd, max(abs(v - consensus) for v in vals))` then only ever widened
  (line 320-323), so `covers_every_reading": all(abs(v - consensus) <= half + 1e-12 for v in
  vals)` (line 344) is true by construction for every input and cannot fail. The code's own
  comment (lines 335-343) says exactly this ("this is a GUARANTEE being published, not a check
  being run... it must not be mistaken for verification"). Flagged per the lens's instruction to
  hunt for vacuous-green checks; not a hidden defect since the author already flagged it, but a
  reader of the JSON output alone (without the source comment) would reasonably mistake
  `covers_every_reading: true` for a passed test.

- **assay.py:736-740, 819-860 (`null_instrument`, `interval_from_hands`, and the `HANDS` dict) —
  dead code.** VERIFIED (repo-wide grep, zero external callers).
  Neither function is called anywhere outside `assay.py`'s own body (`grep -rn
  "null_instrument\|interval_from_hands" --include=*.py .` matches only their own `def` lines).
  `HANDS` (line 807-816) is likewise referenced nowhere else (`grep -rn "\bHANDS\b"` outside
  `assay.py` hits only unrelated substring matches in `cascade_bridge.py`, e.g. "THE ROUTER
  NEVER HANDS OUT..."). `interval_from_hands()` is the function that implements Vol. 0.5 §2
  Theorem 4 as literally described ("readings maps Hand name -> assayed value... the interval
  must cover every signed reading") — the same theorem `custodes.py` cites extensively as its
  own justification — but the production path (`custodes.convene()`) reimplements the covering-
  interval logic independently rather than calling this function, leaving ~65 lines of "the
  Hands as priors" machinery, including a `HANDS` dict describing four standpoints, entirely
  unreachable from any real entry point. `null_instrument()` (Theorem 3(ii), the computed null
  for a degenerate/relic agent) is likewise never invoked — nothing in the generation pipeline
  calls it for a singleton-strategy-set entity, so it's unclear anything currently produces the
  "computed null" the docstring promises.

- **ingest_doc.py:216 — `description[:2000]` truncation on a per-entity extraction field.**
  SUSPECTED as a Hard Rule 0 concern, likely benign in practice.
  `"description": (e.get("description") or "").strip()[:2000]` truncates a single entity's
  extracted description to 2000 characters before it's stored. This is a truncation of extracted
  content, not (per CLAUDE.md's own wording) a "roster, a page list, a chunk list, or an entry
  list" — so it may fall outside Hard Rule 0's literal scope, and given the source chunk fed to
  the model is itself capped at 9000 characters (`CHUNK = 9000`, line 39) covering an entire
  passage rather than one entity, a single entity's description realistically staying under 2000
  chars in ordinary use is plausible. Flagged for the record since it is a silent truncation of
  content the model produced, with no log or flag when it fires.

---

## NOTES

- **pipeline.py:564 (`write_record`) uses a fixed `path + ".tmp"` temp name, not the
  pid/thread-unique naming `silence.write_json` documents as the fix for exactly this hazard.**
  Out of this batch's assigned files (lives in `pipeline.py`), but directly exercised by
  `ingest_doc.py:293`'s call to `write_record`, so noted for cross-reference: `silence.py`'s own
  docstring (lines 302-305) says "Two writers of the same path otherwise collide on the temp
  file itself, and the loser can replace the winner's target with a partial file" — describing
  the exact pattern `write_record`'s own tmp-file line still uses. Whether this is live risk
  depends on whether two processes ever call `write_record` on the same record path
  concurrently (plausible: `ingest_doc.py --mine` + a running `pipeline.py` phase + a
  `catalogue_web` recatalogue could all touch the same source's record file). Flagged for the
  batch owning `pipeline.py`, not fixed here.

- **derivation.py** — read in full; no correctness bugs found. It is a documentation-as-code
  provenance ledger (`LEDGER` dict) plus a graph-integrity checker (`check_graph`,
  `depth`, `provenance`, `scan_constants`). `check_graph()`'s cycle detection is correct (mutual
  self-reference short-circuits via the `seen` set in `depth()`, and `visit()`'s open/done state
  machine correctly reports cycles rather than looping). No caps, no swallowed exceptions beyond
  one appropriately-scoped `except SyntaxError` in `scan_constants` (line 489, logged via
  `silence.note`).

- **style_audit.py, repass_bands.py, lognames.py** — read in full; no correctness, concurrency,
  or Hard-Rule-0 issues found. `repass_bands.py` already gates its write on the return value
  (line 84, citing "run #25") — this is the *correct* pattern that `ingest_doc.py:293` (MAJOR,
  above) fails to follow. `style_audit.py`'s `[:top]`/`[:14]`/`[:8]` slices are all display-only
  formatting of already-fully-computed corpus-wide counters, not caps on what gets scanned or
  scored. `lognames.py` is a 36-line constants module; nothing to find.

- The Custodial Assay fabrication check (Hard Rule 3): no site in these eight modules was found
  that manufactures or rounds a decimal into existence without a cited worksheet. `assay()`
  refuses (`worksheet` required, assay.py:598-601) and `instrument()` refuses identically
  (assay.py:705-709); `_check_scores` raises rather than clamps out-of-range inputs
  (assay.py:431-455). The BLOCKING and first MAJOR findings above are about the *interval/veto*
  machinery around the decimal being unreliable or unreachable, not about the decimal itself
  being fabricated.
