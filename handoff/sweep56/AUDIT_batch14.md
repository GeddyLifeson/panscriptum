# Sweep56 batch14 — audit

Modules read in full, top to bottom (line counts at time of audit): `src/read.py` (1670),
`src/health.py` (1306), `src/ledger_guard.py` (1007), `src/ingest_doc.py` (670),
`src/prose_gate.py` (537, AUDIT ONLY — owner-held safety gate, not edited, no relaxation
recommended), `src/genre.py` (381), `src/wh40k.py` (350), `src/tempus.py` (297).

All findings below are verified against the live source at the time of this audit (line numbers
quoted are the file's own current numbering, confirmed with `grep -n` / `sed -n` immediately
before being written down). No file in this batch was edited.

---

## Findings

### 1. DEFECT — `src/read.py:232` cites a stale line number for its own module

```
# read_entity's chunk-selection filter (read.py:731) already falls back to the whole name
# for exactly this case; this is the same fallback, but phrase-bound rather than a raw
```

`read.py:731` is inside the `_chunk_key()` docstring (unrelated prose about the entity-in-cache-key
fix). The fallback the comment actually means — `keys = [...] or [name.lower()]` — is at
**`read.py:835`**, 104 lines away. Purely a documentation/comment defect (self-citation drift);
no behavioural effect. Matches the audit's "stale line-number citation" class exactly.

### 2. DEFECT — `src/health.py:94` cites a stale line number in `escalation.py`

```
# it is the half proposed to `escalation.py:248`.
```

This is the `SELFTEST_LEDGER_PATH` block's note that `subject=` (passed to `health.record()`)
is the fix for a case the key-only match can't see. `escalation.py:248` is now inside unrelated
prose about `escalate()`'s OWNER/MANAGER level-parsing fallback. The actual call this comment is
about — `health.record("escalation:%s:%s" % (...), rec["what"], subject=rec.get("source"))` —
is at **`escalation.py:320-321`**, already implemented under the same order id
(`5bbbb65e7787`) the health.py comment itself cites. So the citation is stale by ~72 lines, and
the "proposed" framing is also stale — the fix already landed on the escalation.py side.
Comment-only; no behavioural effect.

### 3. QUESTION (low severity) — `src/health.py:537-538`'s "as of this writing" line numbers have
already drifted

```
# Grep for those two strings. As of this writing they sit at dashboard.py:350-360 and
# standards.py:1000-1028.
```

Verified current locations: the `silence.note("dashboard.py:failures")` guard is at
**`dashboard.py:375`**, and `silence.note("standards.py:ledger")` is at **`standards.py:1197`**
(not 1000-1028 — a ~170-line drift). The docstring explicitly anticipates this ("Line numbers in
another file are a citation with a short shelf life") and tells the reader to grep the tag
string instead of trusting the numbers, which is exactly what still works today — the tags
themselves are unchanged and correct. Flagged as a QUESTION rather than a DEFECT because the
mechanism designed to survive drift (the tag) does survive it; only the illustrative line range
is now wrong, and the comment already told the reader not to rely on it.

### 4. DEFECT — `src/prose_gate.py:362-363` — all five cross-file line citations are stale

This is inside `cited_names_for()`'s docstring (layer 4b, assay honesty), explaining why this
call site now passes `on_corrupt` to `cachekey.load`:

```
ON_CORRUPT TRACE (order 2ce520242de8). This was the only `cachekey.load` call site in the
tree that did not pass `on_corrupt` -- feats.py:1454, hostcheck.py:1374, pipeline.py:1399,
read.py:804 and sweep.py:184 all do.
```

Verified actual locations of the `cachekey.load(..., on_corrupt=...)` call in each named file:

| cited                | actual | drift |
|-----------------------|--------|-------|
| `feats.py:1454`       | `feats.py:2059` | 605 lines |
| `hostcheck.py:1374`   | `hostcheck.py:1436` | 62 lines |
| `pipeline.py:1399`    | `pipeline.py:1483` | 84 lines |
| `read.py:804`         | `read.py:819` | 15 lines |
| `sweep.py:184`        | `sweep.py:192` | 8 lines |

All five call sites do genuinely still exist and do still pass `on_corrupt=` (confirmed by
reading each), so the substantive claim in the docstring is correct — only the line numbers are
wrong, one of them by over 600 lines. Reported per the audit brief's instruction to read and
audit `prose_gate.py` without editing it, recommending nothing about the gate's behaviour: this
is a comment-accuracy note only, in the file's own historical/provenance prose, not in any gate
logic. **No change to `prose_gate.py` was made or is being recommended here beyond flagging the
citations for whoever next touches that docstring.**

### 5. DEFECT — `src/tempus.py:75` cites a stale line number in `verify_math.py`

```
# since gained a reader -- verify_math.py:861 walks `DEGENERATE_TIME.values()`. It has one
```

The actual `check(...)` call that walks `T.DEGENERATE_TIME.values()` is at
**`verify_math.py:885-887`** (the `check("degenerate shelves are findings, not rates", ...)`
call). `verify_math.py:861` is now `for _b in ("M1", "M4", "M7", "M10"):`, part of the unrelated
`rung_description_length` check loop just above it. Drift of ~24-26 lines. Comment-only, no
behavioural effect; the substantive claim (verify_math.py does now read `DEGENERATE_TIME`) is
still true.

---

## Nothing found (clean) in the remaining scope

- **`src/read.py`** — beyond finding 1 above (a stale self-citation), no fail-open paths, no
  tautological checks, and no undisclosed caps were found. `cap_chunks`/`--chunks` is
  deliberately made inert (documented, `silence.note("read.py:cap-chunks-ignored")` on use) per
  Hard Rule 0, and `--limit` is loudly marked PARTIAL with a deferred count — neither is a
  silent truncation. The transport ladder (`_ask`/`_ask_ungated`/`_local`), the adaptive gate
  (`_gate`/`_card_gate`, with per-thread re-entrancy tracking to avoid self-deadlock), and the
  chunk/entity caching (`_chunk_key`, `_chunk_put`'s per-writer temp names) all read as
  internally consistent with their own extensive commentary, and I could not find a case where
  the documented fix does not match the code as it stands today.
- **`src/health.py`** — beyond findings 2-3 above, the failure-ledger compare-and-swap
  (`_flush_ledger`/`_flush_samples`/`_cas_land`), the preflight checks (`check_control_chars`,
  `check_context_budget`, `check_api_paths`, `check_caches`, `check_state`), and
  `reopen_stranded`'s read-verify-write-refuse-on-drift sequence all fail closed as documented.
  No bare `except: pass` that swallows a real fault silently — every blanket except block found
  either calls `silence.note(...)` or is explicitly justified inline (e.g. `_drop_tmp`'s
  `except OSError` on a temp file nothing else can be racing).
- **`src/ledger_guard.py`** — the append-only detector (`_one_insertion`), the multiset-based
  `_lost_fraction`/`_substantive_lines`, the two independent truncation floors
  (`check_since_snapshot` vs `check_since_floor`, deliberately different failure modes per Hard
  Rule -1), and the hash-chain verifier (`verify_chain`, including the bytes/chars unit
  reconciliation across the 016fcf397818 schema boundary) all trace through correctly by hand.
  The `pipeline.py:36` cross-file citation was checked and is accurate. `_digest()` truncates
  SHA-256 to 32 hex chars (128 bits); this is adequate for the stated non-adversarial,
  single-writer tamper-evidence purpose the docstring describes and is not flagged as a defect.
- **`src/ingest_doc.py`** — the halt check (`_assert_not_halted`, fail-closed on
  `ImportError`), `record_path`'s ambiguous-match refusal, the oversized-page re-chunking (mirrors
  `read.py:_local_carded`'s pattern, verified the resume-cursor-only-moves-forward claim is
  internally consistent), and the resume-cursor / record-write ordering in `mine()` (advance the
  cursor only after a landed write, roll back `known` on a denied write) all read correctly.
  No undisclosed truncation — the removed `[:2000]` description cap and the removed `[:12]`
  feats cap (also seen in `read.py`) are both correctly gone, matching their comments.
- **`src/prose_gate.py`** (audited, not edited) — layers 1/2 (`gate_open`/`step4_gate_open`,
  strict `is True` / `is not True` identity checks, fail closed on unreadable or non-dict
  config), layer 3 (`floor_ok`/`evidence_ok`, the "a floor of 0 is misconfigured, not permissive"
  fix), and layer 4/4b/4c (`section_shortfall`'s ghost- and extra-entry charging,
  `instrument_shortfall`'s marked/scored/excused/being logic, `unearned_instrument`'s
  cited-evidence lookup through `cachekey` with fail-closed-to-empty-set on any read failure) all
  traced through by hand and are internally consistent with their own commentary. Beyond the
  citation issue in finding 4, I found nothing that looks like a fail-open path, a tautological
  check, or a disclosed-then-reintroduced cap. (See QUESTION below re: `instrument_shortfall`'s
  non-being branch.)
- **`src/genre.py`** — `classify_text`'s `top=None` default and `classify_source`'s refusal of a
  numeric `cap` are both correctly wired (verified `most_common(None)` really does return the
  whole field, so the "no `not ranked` disjunct" comment's claim that `ranked` can never be empty
  holds). No truncation found in the live classification path (`_cut()` is display-only and
  clearly marked as such).
- **`src/wh40k.py`** — mostly literal roster data; `_provenance()`'s 3-tuple/2-tuple handling and
  the gated `silence.write_json` on `main()`'s write are correct and consistent with the sibling
  modules (`halo.py`/`zfighters.py`) it cites.
- **`src/tempus.py`** — beyond finding 5, `apparent_lag_years`'s two-branch return-shape
  consistency (both branches always carry `distance`/`lag_years`/`path`/`note`), the
  `DEGENERATE_TIME` table, and the bit-cost derivations (`rung_description_length`,
  `band_resolution`, `prescience_horizon_bits`, `retrocausality_beta`) all check out
  algebraically against their own stated formulas, including the `lead_time_years > 0` guard in
  `prescience_horizon_bits` (correctly raises rather than silently producing a plausible-looking
  non-positive bit count).

---

## QUESTION for the owner (not a defect, flagged per audit instructions)

**`src/prose_gate.py`, `instrument_shortfall()` (layer 4c).** For a **non-being** entry
(Place/Vessel/Faction/Event), the pass condition reduces to just `marked` — i.e. a non-being
entry that carries an "▣ The Instrument" marker (or even a bare "▣" character anywhere in its
block) passes this layer even if it never actually writes the template's required
"Not applicable — the Instrument measures beings, not [...]" sentence. This matches the
docstring's own stated rule ("a non-being entry needs the marker or the sentence") and is very
likely deliberate — the layer's purpose (per its header comment) is narrowly to catch the
2026-08-25 incident's headline symptom (the section vanishing entirely), not to also verify the
non-being sentence's exact wording, which may be some other layer's job or may be intentionally
left unchecked. Raised as a question rather than a finding because I have no evidence this is
unintended, and per the audit brief I am not recommending any change to this file.

---

## Coverage

Recorded via `sweep_plan.record('run56', [...], batch=14)` for all eight modules listed above —
every one was read in full, top to bottom, in successive chunks.
