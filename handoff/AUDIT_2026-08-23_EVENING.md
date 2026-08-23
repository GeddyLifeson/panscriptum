# EVENING SWEEP — 2026-08-23

Scope: everything changed since the morning audit (the day's fire-forged code — magnitude's
split/epoch/retry weave, cascade widen + local-claim block, identity's epoch doctrine, the
watchdog/supervisor guards, feats' vector vocabulary) plus the full mechanical battery.

Battery results: **86/86 modules import · LINT clean (0 undefined names) · 61,489 files opened,
0 corrupt · verify_math 237/237 · 0 subsystems in a bad state · local and GitHub in sync.**

Legend: **FIXED** = repaired during this sweep.

---

## CRITICAL

**C1. Epoch mandate had a bypass through the split-retry. FIXED.**
`assay_entity` validated the epoch on the FIRST answer, then let the quality-failure retry
replace that answer wholesale — so a junk one-shot carrying a plausible epoch could pass the
mandate and the published accession would wear the junk answer's epoch on the retry's sheet.
The retry is now held to every gate the first answer was: epoch re-derived, re-validated
(deferred on failure), anchor re-clamped.

**C2. Ledger blindness: 35,806 of 38,205 swallowed failures were one probe artefact. FIXED.**
The widened liveness probe (`overnight.running`) noted a ValueError for every formatting row of
its own powershell output, on every call, every cycle. Real failure classes (1,108 URLErrors
from the roll, 48 pool deadlines) were buried under 94% noise, and the swallowed-failures
standard was red for a reason that wasn't a fault. Routine expected structure is now skipped
unrecorded; the polluted class archived; ledger total 38,205 → 2,400 and every remaining line
is a real event.

## HIGH

**H1. Split-gate fabrication direction. FIXED.** `_split_gate` accepted a citation when the
candidate was contained in it (`o in ft`) — which validates a fabricated wrapper written AROUND
a real sentence. Containment now runs one way only: a trimmed copy of a real candidate passes,
an embellished one fails.

**H2. Overwatch's 5 open high findings — triaged, none survive as written:**
- `chain.py pos` off-by-one: **refuted** — prompt numbers 1-based, code subtracts 1; correct.
- `catalogue_web MAX_PER_CATEGORY` TypeError: **stale** — fixed this morning; ledger fingerprint
  should close on the changed digest next round.
- `catalogue_web MAX_PER_SOURCE` guard placement: fair nit (guard fires after category pulls);
  harmless — it exists to refuse a future config change, not to gate this run.
- `cascade stream_chat` no-timeout: the deadline is enforced by the pump thread by design; the
  bench handles the hang case. Working as intended; worth a comment someday.
- `dead_forever` verdict classes: docstring nuance, low.

**H3. Missing `prompt_chars` on the epoch-refusal record. FIXED** (both refusal sites).

## OPERATIONAL (not bugs — the evening tide)

- **Pool at 272 calls/hr, 19% ok**: the free tiers' daily windows are draining (cloudflare and
  cohere EXHAUSTED, groq thinning). This is the meter, not the code — the batch grinds slower
  and defers more until the windows roll. Nothing false is published; `settled()` requeues all.
- **Batch 3 on pre-mandate code**: launched minutes before the epoch edits; its MTG/Realms
  results this round may be unstamped, and the NEXT batch pass refuses-and-redoes them under
  the mandate. No action needed — the mandate self-corrects the backlog.
- **Jace's two accessions** (model-epoch + Living Guildpact) sit DEFERRED behind the batch;
  the mandate's first live firing was one of them (refused an unstamped sheet — by design).
- foreman/overwatch/read cycling as the supervisor restarts them post-bounce — expected.
- Catalogue coverage still reads 4.9% from the stale audit; the foreman's `always`-remedy
  re-measures after the catalogue pass completes.

## VERIFIED SOUND UNDER RE-READ

The whole of `assay_entity`'s new topology (split-first over 30k, pool→local→split fallback,
defer-never-truncate, ceiling clamp, quantity overwrite ordering); `identity`'s epoch doctrine
and directive; the cascade proof-ranked widen and the router local-claim block; the vector
vocabulary additions; `chain.write_result`; the watchdog/supervisor/foreman guard triad
(one watchdog, one supervisor, ceasefire) — holding through multiple cycles, dupes NONE.
