# Sweep 41 — Batch 05 audit

Modules assigned, all read in full, no sampling:

| module | lines |
|---|---|
| `src/cascade_bridge.py` | 1985 |
| `src/completeness.py` | 753 |
| `src/secondopinion.py` | 622 |
| `src/reference.py` | 480 |
| `src/prose_gate.py` | 402 (READ-ONLY per batch instruction — owner-held safety, not edited) |
| `src/hosts.py` | 333 |
| `src/scope.py` | 275 |
| `src/scale_theories.py` | 174 |

Total: 5,024 lines read.

## Findings filed

1. **`4b69c225dbb6` — HOSTS_DOC_SENTINEL_LEAK — MINOR — LOCAL**
   `hosts.hosts_for()` filters the `"pages:"` provenance sentinel off the primary host but not
   the sibling `"doc:"` sentinel (`src/hosts.py:69`), even though `health.py:493` and
   `binding_health.py:1018` both treat the two prefixes as one class, and
   `completeness.py`'s own `SENTINELS = ("pages:", "doc:")` names the pair. Reproduced live:
   `data/WIKI_HOSTS.json` carries one `doc:` primary host today (`Arcanum Worlds (Odyssey of
   the Dragonlords)` → `doc:arcanum-worlds-odyssey-of-the-dragonlords`), and
   `hosts.hosts_for('Arcanum Worlds (Odyssey of the Dragonlords)')` returns that sentinel
   verbatim, as if it were a real, probeable host. `hosts.coverage()` then counts the source
   under `with_a_host`. No caller of `hosts_for()` exists yet elsewhere in `src/`, so the blast
   radius today is the stats line and `--show`, not a live network probe — but the function's
   own contract ("every host this source can be READ from") is violated for this one case, and
   the fix is a one-line convention match against the sibling files.

2. **`6e6954f261e0` — PROSE_GATE_INSTRUMENT_UNCHECKED — MAJOR — OWNER (question, not an edit)**
   `prose_gate.py`'s `REQUIRED_PER_ENTRY = ("Shelfmark:", "Class:", "Magnitude:", "Threads:")`
   — the structural check `section_shortfall()`/`assert_block_complete()` runs per entry — does
   not include the `▣ The Instrument` section, nor `Attestation:`/`The Record.`/
   `Contradictions.`/`Marginalia.`. The module's own docstring names Instrument-block loss as
   one of the two documented symptoms of the 2026-08-25 incident this exact layer exists to
   catch: *"only 113 [of 1,268] kept an Instrument block"* — a 91% loss, worse than the 71%
   Threads loss that IS checked today.

   Empirically reproduced this shift: a synthetic two-entry block carrying Shelfmark, Class,
   Magnitude, Attestation and Threads for every entry, but with the Instrument section dropped
   entirely, scores `section_shortfall() == (10, 10, [])` — 100%, nothing missing — and passes
   `assert_block_complete()` cleanly. `unearned_instrument()` (layer 4b) does not catch it
   either, because that check only fires on a *fabricated* score when one is present; it has no
   opinion about a section that never appears at all. So a chapter reproducing the original
   incident's own headline symptom would clear every layer-4 and layer-4b check as written
   today.

   Filed as a question, not a proposed edit, per this batch's standing instruction: this is the
   owner-held prose safety a prior sweep already deleted once by acting on its own reading of
   "looks unnecessary." This finding runs the other direction — it says the check may be
   *under*-strict, in exactly the place its own incident narrative calls out — and asks the
   owner to rule on whether `REQUIRED_PER_ENTRY` (or an equivalent parallel check) should be
   widened to require an Instrument marker (a real scored line, or the template's own "Not
   applicable" text for Place/Vessel/Faction/Event classes), the same way `Threads:` is
   required now. Two honest readings are given in the order body: (a) oversight, or (b) the
   Instrument's structural presence was deliberately left to `unearned_instrument()`'s narrower
   fabrication check as an accepted residual risk. `prose_gate.py` itself was not touched, and
   `prose_enabled`/`step4_enabled` were not discussed as candidates for opening.

## Verified and NOT filed (checked against source, found to be deliberate/already covered)

- **`completeness.py`: a source whose category probes all answer cleanly but none clears any
  probed category (`sizes` empty, `failed == 0`) returns `None` from `work()` and gets NO row
  in `COMPLETENESS.json`** — no `unreliable` marker, unlike every other failure mode in the same
  function. This looked, on first read, like exactly the "silently excluded from a measurement,
  reported as an ordinary negative" founding defect the module exists to fix. Checked against
  `verify_math.py:1707-1708` (`check("genuine absence (every probe answered, no categories) ->
  row dropped", len(_CP.audit(workers=1)), 0)`) and the surrounding fixture: this exact case is
  an explicit, asserted, regression-tested design decision, not a gap. Confirmed live that all
  216 sources currently have a `COMPLETENESS.json` row (0 missing against the union of
  `WIKI_HOSTS.json` and `data/records/`), so the path is not silently dropping anything today
  either. Not filed — verifying this before filing is exactly what the audit brief asked for.
- **`hosts.py` `--discover`'s `str(src)[:39]` source-name truncation** (line ~310) — this is the
  already-known, already-filed instance named in the batch brief (order `c6ca8a8f8e55`).
  Confirmed still present in source; not re-filed.
- **`scale_theories.py` has zero functional callers anywhere in `src/`** (only mentioned in
  comments in `descending_ladder.py`, `drill.py`, `liveness.py`, `tempus.py`, never imported or
  called). This is a real, live fact, but it is already tracked as an open order
  (`01695fe3ef26`, `SWEEP34_FINDING`, filed and still open in `state/workorders.json`) — not
  re-filed.
- **`cascade_bridge.py` metrics: a successful call whose parsed JSON is a bare list/bool/number
  rather than a dict** writes `"model": "tried:<bucket>"` instead of the bare bucket name in
  `state/model_metrics.jsonl` (the `isinstance(got, dict)` branch in `ask()`'s metric row).
  Checked whether any reader (`dashboard.py`, `standards.py`) parses that field for per-bucket
  attribution — neither does; both aggregate by `tag`/pool, not by the `model` field. Every
  current caller of `cascade_bridge.ask()` also passes an object-type JSON schema, so the
  non-dict branch is not reachable through any live call path today. Theoretical, not
  currently reachable, and not currently read by anything that would misattribute from it — not
  filed.
- **`cascade_bridge.dead_forever()`'s `PROOF_TTL` (1h) discarding the whole proof, including
  permanent 401/402/404/410 verdicts, once `POOL_PROOF.json` goes stale** — considered as a
  possible re-admission of a genuinely dead bucket into rotation. Traced the consequence: a
  re-admitted dead bucket hits the ordinary `_ask_call` failure path on its very next real
  attempt, which re-classifies it via `permanent_refusal()` and re-benches it (`AUTH_BENCH`, 4h)
  independently of `dead_forever()`. Self-healing by construction, not a silent loss — not
  filed.
- **`cascade_bridge._extract_json`'s brace-depth counter is not string-aware** (a literal `{`/
  `}` inside a quoted sentence value could close the object early). Failure mode is fail-safe by
  the function's own contract (`json.loads` fails → tries the next `{`, or returns `None`,
  which callers already treat as "failed call," never as an empty/wrong result) — not a silent
  wrong answer. Narrow, pre-existing, and low-value; not filed.
- **`prose_gate.py` `_AXIS_RE` matching only Strength/Dexterity/Constitution/Intelligence/
  Wisdom/Charisma** — checked against `prompts/system_style.txt`'s Entry Template (the
  "six-axis Instrument," scored 1–30) rather than assumed to be a mismatch against the
  Custodial Assay's eleven Measures (a different, later-pass system per Hard Rule 3). Confirmed
  correct: this is the right vocabulary for the per-entry Instrument block. Not filed.

## Coverage

`sweep_plan.record('run41', [the 8 modules above], batch=5)` — recorded.
