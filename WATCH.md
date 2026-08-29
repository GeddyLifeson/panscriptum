# OVERWATCH

round 152  ·  last run 2026-08-29 09:42

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 273,179 inspected (deep scan as of round 151)
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**15 open** (4 high). Newest first.

- **anchors.py** `run` — [HIGH] The function is called and its result is used to determine exit code
  - says: A CHECK WHOSE RESULT IS PRINTED AND DISCARDED CANNOT FAIL
- **workorders.py** `file_order` — [HIGH] Creates a new order and writes it to the queue, but does not handle the case where the queue write fails, leading to potential data loss
  - says: Open (or refresh) one work order. -> the order.
- **verify_math.py** `check` — [HIGH] the check is using a variable that was not defined in the current scope
  - says: a reasoning model's truncated generation reads as FLOW, not a wedge
- **rosetta.py** `main` — [HIGH] The function returns 0 unconditionally, but the code comments indicate that it should return 1 if there are disagreements.
  - says: The exit code has to carry the verdict, not just the printout.
- **feats_index.py** `_norm` — [MEDIUM] Folds alphanumeric-only, does not strip parentheticals
  - says: Fold a name to its comparable core. THIS DOES NOT STRIP A PARENTHETICAL
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Compares the normalized qualifiers for equality, but the code's comment says that this is not literal string equality and that the gate is absolute. However, the code actually chec
  - says: Two names may only be compared if their qualifiers agree.
- **workorders.py** `resolve` — [MEDIUM] resolve
  - says: resolve_code
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
- **overnight.py** `run` — [MEDIUM] cannot run after the reader because pipeline is started in the background and the keeper re-asserts the standing set every 300s
  - says: Runs after the reader so it sees the evidence the reader just produced
- **navtree.py** `register_for` — [MEDIUM] returns a register for a node, but the logic for tie-breaking is flawed and non-deterministic
  - says: returns a register for a node

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
