# OVERWATCH

round 53  ·  last run 2026-08-23 23:25

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 58,979 inspected
- catalogued sources with no host: **20** Clockwork Angels (Rush), Curious DM Investigations (the Sharkin), Dr. Firestorm'
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**6 open** (2 high). Newest first.

- **feats.py** `api` — [HIGH] May make a MediaWiki API call to the wrong endpoint if the wiki is not Fandom or Wikipedia
  - says: Makes a MediaWiki API call to the correct endpoint
- **endpoint.py** `fetch_html` — [HIGH] The function `fetch_html` uses a hardcoded timeout value of 45 seconds, which contradicts the comment that says it should be polite
  - says: {url: text} for a list of ordinary web pages.
- **endpoint.py** `register` — [MEDIUM] The function `register` does not handle the case where the source already exists in the dictionary, which could lead to duplicate URLs
  - says: Record where a source's material actually lives.
- **endpoint.py** `exists_raw` — [MEDIUM] The function `exists_raw` calls `fetch_raw` but the docstring does not mention this function
  - says: Which of these titles the host actually serves. The raw-mode answer to a titles probe.
- **custodes.py** `ATTESTATION_QUALITY` — [MEDIUM] hardcoded values
  - says: derived from _ATT_BASE
- **autostart.py** `ap.add_argument('--read-hours', type=float, default=10)` — [MEDIUM] read-hours argument is used to start the supervisor
  - says: read-hours argument is used to determine the hours to read

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
