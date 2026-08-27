# sweep35 batch16 audit

Modules read in full (3,583 lines): src/local_agent.py, src/publish.py, src/escalation.py,
src/scout.py, src/ingest_doc.py, src/tempus.py, src/profile.py, src/resonance.py.

## Filed findings

1. **e319b1c9a804** (BLOCKING) -- `local_agent.py` main()/run() never calls
   `escalation.assert_clear()`. The only lane where a model may write to `src/` does not check
   the plant-wide halt at all, and is not even in verify_math's own S20p `_INTERLOCKED` tuple
   (dashboard/feats/foreman/overnight/overwatch/pipeline/publish/read.py), so nothing polices
   its absence either. Confirmed by grep: the file's only two `escalation` imports both feed
   `escalate(...)` (raising an alarm), never `assert_clear`. `drill.drill_local_agent()` tests
   the five known write-gate bypasses but never tests the halt check.

2. **1e0c26421a48** (BLOCKING) -- a sixth bypass class of the local_agent write gate, same shape
   as the five already fixed (case, name prefix, NTFS ADS, case-sensitive extension, unlisted
   directory): a filesystem reparse point (an NTFS directory junction, `mklink /J`, no admin
   required) planted under a writable prefix (`handoff/`, `prompts/`, `src/`) and pointing at a
   protected target (`state/`, `data/records/`, `reference/keystone_volumes/`). `_safe()` and
   `t_propose_patch()` do every check on the path STRING (`os.path.abspath`/`splitdrive`,
   `.startswith`); neither calls `os.path.realpath` or otherwise resolves a reparse point
   anywhere in the file (grep confirms zero hits for realpath/readlink/reparse/junction/symlink).
   `open(full, "w")` follows the junction at the OS level regardless of what the string checks
   concluded. Named exact input: `propose_patch(path="handoff/escape/HALT.json", ...)` with
   `handoff/escape` a junction to `..\state`.

3. **f467f662be4b** (MAJOR) -- Threnody's curl-veto is a safety that exists in a file but is not
   in effect. `resonance.hodge_decompose`/`resonance_strength` have zero production callers
   anywhere in `src/` (only verify_math's own unit tests import `resonance`, and only exercise
   `incomparability_rate`). `custodes.convene()`'s docstring claims "`eta` (from
   `resonance.hodge_decompose`) lets Threnody exercise her veto," and the veto branch is real
   code -- but the sole production caller, `anchors.py:190`, never passes `eta=`, so it defaults
   to `None` and the veto can never fire on real assay data. The only place `eta` is ever
   non-`None` is a hand-typed literal (`eta=0.70`) in `custodes.py`'s own demo `main()` output
   and in verify_math test fixtures.

## Not filed (already covered by other batches / stale)

- `tempus.DEGENERATE_TIME` dead code: already filed (0291835411d9).
- `resonance.py` "unimported anywhere" (c16499b0a50b, SWEEP33): now stale in its literal
  claim -- verify_math.py does import it for tests -- but the deeper defect (no production
  caller, veto never wired to real data) is real and is what finding 3 above documents freshly.
- `local_agent.py:578-584` blast-cap `except Exception: pass`: already filed (4be547515bd9).
- `local_agent.py:761-767` unhandled dispatch args: already filed (a75cd9ac1273).
- `publish.py` secret scanner / ledger-guard / mutate-lock / halt-import guards: read in full,
  all found already hardened against fail-open (streamed scan with UNSCANNABLE-as-hit, entropy
  + structural double lock, `except ImportError` now raises rather than passing, refused-push
  now returns rc=1). No new fail-open path found here this shift.
- `escalation.py`: read in full. `clear()`'s runtime person-at-CLI check, the halt-file
  fail-closed read, and `_raise_halt`/`clear`'s write-verdict handling all held up under
  adversarial reading; no lift/bypass path found.
- `scout.py`, `ingest_doc.py`, `profile.py`: read in full, no halt bypass, no fail-open write
  path, no silent cap found. Neither has an `escalation.assert_clear()` call, but neither is a
  src/-write lane or a public-push lane, so this was judged lower-value than the local_agent gap
  and not filed separately.

## Coverage recorded

`sweep_plan.record('run35', [local_agent.py, publish.py, escalation.py, scout.py, ingest_doc.py,
tempus.py, profile.py, resonance.py], batch=16)` -- done.
