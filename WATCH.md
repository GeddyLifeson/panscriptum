# OVERWATCH

round 149  ·  last run 2026-08-29 07:10

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 272,014 inspected (deep scan as of round 145)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**20 open** (7 high). Newest first.

- **verify_math.py** `check` — [HIGH] the check is using a variable that was not defined in the current scope
  - says: a reasoning model's truncated generation reads as FLOW, not a wedge
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
- **rosetta.py** `main` — [HIGH] The function returns 0 unconditionally, but the code comments indicate that it should return 1 if there are disagreements.
  - says: The exit code has to carry the verdict, not just the printout.
- **verify_math.py** `_own_nodes20p` — [MEDIUM] Yields nodes of `fn` including nested functions, but skips the nested functions' nodes.
  - says: Every node belonging to `fn` ITSELF, not to a function nested inside it.
- **verify_math.py** `_writes_the_config20p` — [MEDIUM] Checks if a function both names 'config.yaml' and opens something in write mode.
  - says: Every node belonging to `fn` ITSELF, not to a function nested inside it.
- **verify_math.py** `check` — [MEDIUM] the check is for a literal string match, but the comment says it should check the AST for the correct behavior
  - says: check('the auth bench is still four hours', ...)
- **verify_math.py** `measure_bit_value` — [MEDIUM] the docstring quotes the value the function returns, but the worked example still uses the old cumulative figure
  - says: pins PROSE to DATA -- the only way this particular rot cannot recur silently
- **tiers.py** `deliberate_joins` — [MEDIUM] returns deliberate joins, but the comment says it's for explaining why a xenoverse is 'artificial'
  - says: why a xenoverse is 'artificial'
- **sweep_plan.py** `covered_by` — [MEDIUM] returns a set of modules covered by a run, but the code for covered_by is not provided here and may not be implemented correctly
  - says: A membership question deserves a membership answer.
- **standards.py** `fab` — [MEDIUM] fabrication rate calculation
  - says: sentences that survive the verbatim check
- **standards.py** `ollama_token_flow` — [MEDIUM] Derives the context window from config.yaml and checks if any metrics row has a tps in the last 15 minutes
  - says: Does a generation actually COMPLETE? The third liveness lesson in two days.
- **secondopinion.py** `run` — [MEDIUM] calls a function named 'run' which is not defined in the provided code slice
  - says: returns the same ground as the comparison
- **secondopinion.py** `mine_says` — [MEDIUM] calls a function named 'mine_says' which is not defined in the provided code slice
  - says: returns the same ground as the comparison
- **scout.py** `sweep` — [MEDIUM] Sorts by last-attempted first, but the code uses the old ordering logic which sorts by entry count and then longest-waiting.
  - says: Scout the hostless sources, oldest attempt first.
- **overnight.py** `run` — [MEDIUM] cannot run after the reader because pipeline is started in the background and the keeper re-asserts the standing set every 300s
  - says: Runs after the reader so it sees the evidence the reader just produced
- **navtree.py** `register_for` — [MEDIUM] returns a register for a node, but the logic for tie-breaking is flawed and non-deterministic
  - says: returns a register for a node

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
