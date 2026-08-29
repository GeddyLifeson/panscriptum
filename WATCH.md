# OVERWATCH

round 145  ·  last run 2026-08-29 04:32

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 272,014 inspected
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**14 open** (2 high). Newest first.

- **rosetta.py** `main` — [HIGH] The function returns 0 unconditionally, but the code comments indicate that it should return 1 if there are disagreements.
  - says: The exit code has to carry the verdict, not just the printout.
- **publish.py** `push` — [HIGH] Raises PushHeld if a commit could not be landed, but does not return True or False as described
  - says: Commit and push. -> True if it landed, False if there was nothing to send.
- **reference.py** `landed` — [MEDIUM] is assigned the result of write_json, which returns a boolean indicating success of the write operation
  - says: indicates whether the reconstructions landed inside the interval
- **publish.py** `codewatch.claim_singleton` — [MEDIUM] claims a singleton but does not prevent multiple instances from running
  - says: prevent multiple instances of the same daemon from running
- **publish.py** `git` — [MEDIUM] git is used to execute git commands, but the code does not handle the case where git commands may fail or return non-zero exit codes
  - says: git is a function that executes git commands
- **policy.py** `vacuous` — [MEDIUM] A rule that PASSED while looking at a field that does not exist and the operator is not 'absent'.
  - says: A rule that PASSED while looking at a field that does not exist. Not a failure -- but not evidence of anything either, and the only place it is ever visible.
- **pipeline.py** `IMPLEMENTED` — [MEDIUM] built from PHASES but still requires manual updates when phases are added or removed
  - says: BUILT FROM PHASES, NOT HAND-MAINTAINED.
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
- **magnitude.py** `main` — [MEDIUM] always returns 0, but the script may have failed
  - says: exits with 0 on success

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
