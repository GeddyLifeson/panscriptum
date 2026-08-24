# OVERWATCH

round 51  ·  last run 2026-08-23 22:29

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 58,979 inspected
- catalogued sources with no host: **20** Clockwork Angels (Rush), Curious DM Investigations (the Sharkin), Dr. Firestorm'
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**11 open** (2 high). Newest first.

- **feats.py** `api` — [HIGH] May make a MediaWiki API call to the wrong endpoint if the wiki is not Fandom or Wikipedia
  - says: Makes a MediaWiki API call to the correct endpoint
- **endpoint.py** `fetch_html` — [HIGH] The function `fetch_html` uses a hardcoded timeout value of 45 seconds, which contradicts the comment that says it should be polite
  - says: {url: text} for a list of ordinary web pages.
- **endpoint.py** `register` — [MEDIUM] The function `register` does not handle the case where the source already exists in the dictionary, which could lead to duplicate URLs
  - says: Record where a source's material actually lives.
- **endpoint.py** `exists_raw` — [MEDIUM] The function `exists_raw` calls `fetch_raw` but the docstring does not mention this function
  - says: Which of these titles the host actually serves. The raw-mode answer to a titles probe.
- **endpoint.py** `fetch_raw` — [MEDIUM] The function `fetch_raw` is called with `workers=workers` but the docstring does not mention this parameter
  - says: Fetch raw content from URLs derived from titles
- **custodes.py** `ATTESTATION_QUALITY` — [MEDIUM] hardcoded values
  - says: derived from _ATT_BASE
- **cascade_bridge.py** `_bury` — [MEDIUM] Does not check if _DEAD is None before trying to access it
  - says: Bury a bucket for a certain amount of time
- **cascade_bridge.py** `dead_forever` — [MEDIUM] Does not check if rows is None before trying to iterate over it
  - says: Buckets excluded by proof — and ONLY for reasons that cannot fix themselves.
- **cascade_bridge.py** `_pace` — [MEDIUM] Does not check if gap is None before trying to compare it to 0.0
  - says: Block until this bucket's turn. One waiter at a time per bucket, so the queue is orderly.
- **cascade_bridge.py** `_interval` — [MEDIUM] Returns 0.0 if rpm is not found or is <= 0, but does not check if rpm is None before trying to divide by it
  - says: Minimum seconds between entries to this bucket, from its own declared rate.
- **autostart.py** `ap.add_argument('--read-hours', type=float, default=10)` — [MEDIUM] read-hours argument is used to start the supervisor
  - says: read-hours argument is used to determine the hours to read

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
