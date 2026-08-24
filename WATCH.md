# OVERWATCH

round 55  ·  last run 2026-08-24 00:14

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 60,826 inspected
- catalogued sources with no host: **20** Clockwork Angels (Rush), Curious DM Investigations (the Sharkin), Dr. Firestorm'
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**7 open** (3 high). Newest first.

- **manifest_builder.py** `load_record` — [HIGH] The function incorrectly checks `norm_target in norm_fname` (substring containment) and `norm_target.startswith(norm_fname)` (prefix containment), but the logic is reversed: it sho
  - says: Finds the best matching record file by checking if the normalized source name is a substring of the normalized filename or if the normalized filename is a prefi
- **foreman.py** `kill_duplicate_jobs` — [HIGH] The function uses `started.group(1)` to extract the creation timestamp, but if the `started` regex does not match, it defaults to a string of '9's. This can lead to incorrect sorti
  - says: Keep the OLDEST instance of each job and end the rest.
- **feats.py** `api` — [HIGH] May make a MediaWiki API call to the wrong endpoint if the wiki is not Fandom or Wikipedia
  - says: Makes a MediaWiki API call to the correct endpoint
- **foreman.py** `kill_stalled_job` — [MEDIUM] The function attempts to kill processes based on a job name parsed from a string, but the regex pattern used to extract job names (`_re.findall(r"([A-Za-z0-9_]+) \(\d+ min", str(ro
  - says: A job that is UP and writing nothing is worse than a job that is down.
- **endpoint.py** `register` — [MEDIUM] The function `register` does not handle the case where the source already exists in the dictionary, which could lead to duplicate URLs
  - says: Record where a source's material actually lives.
- **endpoint.py** `exists_raw` — [MEDIUM] The function `exists_raw` calls `fetch_raw` but the docstring does not mention this function
  - says: Which of these titles the host actually serves. The raw-mode answer to a titles probe.
- **autostart.py** `ap.add_argument('--read-hours', type=float, default=10)` — [MEDIUM] read-hours argument is used to start the supervisor
  - says: read-hours argument is used to determine the hours to read

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
