# OVERWATCH

round 179  ·  last run 2026-08-29 22:17

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 276,686 inspected (deep scan as of round 175)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**6 open** (2 high). Newest first.

- **binding_health.py** `canary` — [HIGH] The function is named 'canary' but the code does not perform any canary-related logic or data collection. It simply returns a record of probe results without any canary-specific pr
  - says: All three probes for one host, plus its identity when the titles failed. -> record.
- **binding_health.py** `quarantine` — [HIGH] Can overwrite existing records without compare-and-swap, leading to data loss.
  - says: Record a host as failing, WITH ITS REASON. Never a silent skip, never a deletion.
- **coverage.py** `state_of` — [MEDIUM] returns (state, n_feats, n_pages) for a file, but in the code, it's called with `state_of(host, e['name'])` which may not be the correct usage as the function is supposed to take a
  - says: -> (state, n_feats, n_pages) for ONE candidate file, or None if it is not usable.
- **chain.py** `local_unmatched` — [MEDIUM] local_unmatched[side] += 1
  - says: THE WHOLE NAME IS THE KEY, not `side[:40]`
- **chain.py** `unanswered` — [MEDIUM] got is None is exactly 'no model answered'
  - says: got is None
- **binding_health.py** `quarantined` — [MEDIUM] Returns hosts with retry_after > now, but the docstring says it returns hosts that are quarantined and not yet released.
  - says: Only those whose retry-after has not yet passed.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
