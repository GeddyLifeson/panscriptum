# OVERWATCH

round 142  ·  last run 2026-08-29 03:17

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **0** of 271,124 inspected (deep scan as of round 139)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**12 open** (3 high). Newest first.

- **navtree.py** `write_json` — [HIGH] writes to the file
  - says: reads whatever file IS on disk
- **magnitude.py** `verify` — [HIGH] decides on the SENTENCE alone
  - says: the entity must be the DOER
- **local_agent.py** `t_propose_patch` — [HIGH] does not handle failed reverts, does not trigger exit code
  - says: A FAILED REVERT MUST REACH THE EXIT CODE.
- **overnight.py** `run` — [MEDIUM] cannot run after the reader because pipeline is started in the background and the keeper re-asserts the standing set every 300s
  - says: Runs after the reader so it sees the evidence the reader just produced
- **overnight.py** `_keep_warm` — [MEDIUM] Sends a request to the Ollama API to keep the model warm at the configured num_ctx, but does not actually maintain the model resident at that size.
  - says: Hold the model resident AT THE CONFIGURED num_ctx.
- **overnight.py** `start` — [MEDIUM] Launches a job and returns a dictionary with the process and file handle, but the function is named 'start' which implies it should not wait, which it does not. However, the functi
  - says: Launch a job without waiting for it.
- **navtree.py** `max` — [MEDIUM] returns the maximum register with tie-breaking based on count and name, but the tie-breaking is non-deterministic due to the use of set
  - says: returns the maximum register with tie-breaking based on count and name
- **navtree.py** `register_for` — [MEDIUM] returns a register for a node, but the logic for tie-breaking is flawed and non-deterministic
  - says: returns a register for a node
- **manifest_builder.py** `volume_code` — [MEDIUM] The code assigns volume numbers based on sorted source names, but the logic for generating the volume code may not correctly reflect the intended deterministic assignment based on 
  - says: Volume numbers are assigned deterministically by sorted source name so the address of a given book is stable across rebuilds.
- **manifest_builder.py** `volume_code` — [MEDIUM] volume_code is assigned based on sorted source names, but the code does not ensure that the Volume numbers are assigned correctly according to the Series code and source name order
  - says: Resolve each source to its Series code first, THEN hand out Volume numbers where a Series holds more than one source.
- **magnitude.py** `main` — [MEDIUM] always returns 0, but the script may have failed
  - says: exits with 0 on success
- **magnitude.py** `run_batch` — [MEDIUM] ASSAYS.json is not rewritten on each completion, but instead loaded once at the beginning and then overwritten at the end
  - says: Written to be killed. The roll runs for hours against a rate-limited pool, and a crash at hour three must not cost hours one and two -- so ASSAYS.json is rewrit

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
