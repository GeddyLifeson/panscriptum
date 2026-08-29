# OVERWATCH

round 147  ·  last run 2026-08-29 06:02

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 272,014 inspected (deep scan as of round 145)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**21 open** (8 high). Newest first.

- **standards.py** `fab` — [HIGH] UNMEASURED is green by absence
  - says: UNMEASURED IS NOT GREEN
- **standards.py** `fab` — [HIGH] sentences that are fabricated
  - says: sentences that survive the verbatim check
- **standards.py** `ollama_token_flow` — [HIGH] Hardcodes `num_ctx: 512` instead of deriving it from `config.yaml`
  - says: Does a generation actually COMPLETE? The third liveness lesson in two days.
- **standards.py** `unans_files` — [HIGH] unans_files is used but never defined in this file or its imports
  - says: Everything above measures whether the machinery RUNS. These measure whether what it produced can be believed, which is a different question and the library is f
- **standards.py** `fandom_ipv4_reachable` — [HIGH] The function does not enforce IPv4-only connections, and the docstring's claim about the family being the whole point is contradicted by the code's behavior.
  - says: Can this machine open a TCP connection to fandom's edge OVER IPv4?
- **scout.py** `_stamp` — [HIGH] does not modify the file at all
  - says: CURRENT file at write time, so a concurrent stamp from another process is merged rather than overwritten.
- **rosetta.py** `main` — [HIGH] The function returns 0 unconditionally, but the code comments indicate that it should return 1 if there are disagreements.
  - says: The exit code has to carry the verdict, not just the printout.
- **publish.py** `push` — [HIGH] Raises PushHeld if a commit could not be landed, but does not return True or False as described
  - says: Commit and push. -> True if it landed, False if there was nothing to send.
- **standards.py** `fab` — [MEDIUM] fabrication rate calculation
  - says: sentences that survive the verbatim check
- **standards.py** `ollama_token_flow` — [MEDIUM] Derives the context window from config.yaml and checks if any metrics row has a tps in the last 15 minutes
  - says: Does a generation actually COMPLETE? The third liveness lesson in two days.
- **secondopinion.py** `run` — [MEDIUM] calls a function named 'run' which is not defined in the provided code slice
  - says: returns the same ground as the comparison
- **secondopinion.py** `mine_says` — [MEDIUM] calls a function named 'mine_says' which is not defined in the provided code slice
  - says: returns the same ground as the comparison
- **secondopinion.py** `_vulture` — [MEDIUM] The function uses min_confidence=90, which is correct, but the docstring's explanation about confidence levels is misleading. The code does not use the confidence parameter in the 
  - says: Confidence 90, not 60. At 60 vulture reports every uncalled public function in a library of entry points and dispatch tables -- 86 of them here, almost all legi
- **scout.py** `sweep` — [MEDIUM] Sorts by last-attempted first, but the code uses the old ordering logic which sorts by entry count and then longest-waiting.
  - says: Scout the hostless sources, oldest attempt first.
- **scout.py** `verify` — [MEDIUM] Return a generic error message for any exception.
  - says: Prove each answer before believing it.
- **reference.py** `landed` — [MEDIUM] is assigned the result of write_json, which returns a boolean indicating success of the write operation
  - says: indicates whether the reconstructions landed inside the interval
- **publish.py** `codewatch.claim_singleton` — [MEDIUM] claims a singleton but does not prevent multiple instances from running
  - says: prevent multiple instances of the same daemon from running
- **publish.py** `git` — [MEDIUM] git is used to execute git commands, but the code does not handle the case where git commands may fail or return non-zero exit codes
  - says: git is a function that executes git commands
- **policy.py** `vacuous` — [MEDIUM] A rule that PASSED while looking at a field that does not exist and the operator is not 'absent'.
  - says: A rule that PASSED while looking at a field that does not exist. Not a failure -- but not evidence of anything either, and the only place it is ever visible.
- **overnight.py** `run` — [MEDIUM] cannot run after the reader because pipeline is started in the background and the keeper re-asserts the standing set every 300s
  - says: Runs after the reader so it sees the evidence the reader just produced
- **navtree.py** `register_for` — [MEDIUM] returns a register for a node, but the logic for tie-breaking is flawed and non-deterministic
  - says: returns a register for a node

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
