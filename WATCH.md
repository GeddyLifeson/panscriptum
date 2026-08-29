# OVERWATCH

round 128  ·  last run 2026-08-28 21:17

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **1** of 269,929 inspected (deep scan as of round 127)  — handoff\run36\sweep_plan.json — malformed JSON: Extra data: line 213 column 1 (char 3102)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**7 open** (3 high). Newest first.

- **standards.py** `fab` — [HIGH] can be None or a value
  - says: UNMEASURED IS NOT GREEN
- **standards.py** `ollama_token_flow` — [HIGH] Hardcodes `num_ctx: 512` while the code around it says it should derive the window from `config.yaml`
  - says: Does a generation actually COMPLETE? The third liveness lesson in two days.
- **rosetta.py** `main` — [HIGH] The function returns 0 unconditionally, ignoring the bad list and the printout.
  - says: The exit code has to carry the verdict, not just the printout.
- **sweep_plan.py** `silence` — [MEDIUM] imported but not used in the code
  - says: imported to handle errors
- **suppressions.py** `problems` — [MEDIUM] returns a list of problems, including expired and dangling suppressions, but the code does not actually check for expiration or dangling paths correctly
  - says: -> [problems]. An expired or dangling suppression is a FAULT, not a silent pass.
- **standards.py** `report` — [MEDIUM] the code uses a _rank dictionary that sorts 'high' as 0, 'medium' as 1, and 'low' as 2, which would sort high first, then medium, then low. However, the comment suggests that the r
  - says: By RANK, not alphabetically. Sorting the severity strings gives high, low, medium -- so the CLI report buried every medium work order below the lows, which is t
- **standards.py** `fandom_ipv4_reachable` — [MEDIUM] The function does not enforce IPv4-only connections, and the host parameter is not properly validated to ensure IPv4 resolution.
  - says: Can this machine open a TCP connection to fandom's edge OVER IPv4?

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
