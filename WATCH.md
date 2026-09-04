# OVERWATCH

round 329  ·  last run 2026-09-04 03:52

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 293,038 inspected (deep scan as of round 325)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**24 open** (1 high). Newest first.

- **local_agent.py** `run` — [HIGH] The function `run` does not check for a halt, but the comment claims it does.
  - says: THE HALT IS CHECKED HERE, AND UNTIL RUN #35 IT WAS NOT CHECKED ANYWHERE ON THIS LANE.
- **catalogue_models.py** `LAST_WRITE_LANDED` — [MEDIUM] used as a flag to determine if the write to disk was successful
  - says: ATOMIC: standards.py polls PROVIDER_MODELS.json on its own cycle.
- **catalogue_models.py** `sweep` — [MEDIUM] The code processes providers based on their outcome, but the comment indicates that the code should consider the truthiness of the outcome, not just the outcome itself.
  - says: ON THE OUTCOME, NOT ON TRUTHINESS (sweep42-batch14).
- **local_agent.py** `apply` — [MEDIUM] returns a staged patch without applying it
  - says: run started with --no-apply; patch recorded for the audit trail
- **corpus_db.py** `code` — [MEDIUM] code is set to None when the resolver is unavailable, and when there's an exception during resolution, but the comment says that NULL means unshelved and only the resolver may say so. However, the code is set to None in cases where the resolver is unavailable or an exception occurs, which may not be correct according to the comment's contract.
  - says: RESOLVED, UNASSIGNED, OR NEVER ASKED -- THREE STATES, AND TWO OF THEM USED TO SHARE A SPELLING. `code = None` was initialised, the resolver was called inside a try/except that only `silence.note()`d, and the next line's comment stated the contract the except clause then broke: NULL means unshelved, and only the resolver may say so. On any exception NULL was written anyway. That matters far more than one row, because `address._load_spine_codes()` raises OUTRIGHT if data/CHARTER_SPINE_CODES.json is missing or unparseable, and `import address` still succeeds -- so `_spine_for` is truthy, the guard above catches nothing, and one unreadable data file makes ALL 216 sources report as unshelved. The `unaddressed` canned query and the Datasette page then present a whole-roll curatorial backlog, which is exactly the misreading this module's header spends fifteen lines on and nearly acted on once already. The only trace was a note. Now the failure gets its own value, is counted into `meta`, and is reported by the rebuild -- so the index can say "I could not ask" instead of answering for the resolver. (order 25266fa8c2dc)
- **chain.py** `kept` — [MEDIUM] recorded as genuine disagreement
  - says: recorded as genuine disagreement
- **chain.py** `split` — [MEDIUM] split by epoch
  - says: split by epoch
- **workorders.py** `shown` — [MEDIUM] shown is set to LADDER (show everything) by default, and only changes to a single rung if a.handler is valid
  - says: An unknown rung REFUSES rather than falling back to "show everything"
- **secondopinion.py** `mine` — [MEDIUM] the code says it does
  - says: the code says it does
- **resync_roll.py** `have` — [MEDIUM] count of sources with entry_count > 0
  - says: count of sources catalogued
- **resync_roll.py** `relabelled` — [MEDIUM] THE VERDICT IS NOT OPTIONAL
  - says: THE VERDICT IS NOT OPTIONAL
- **resync_roll.py** `relabelled` — [MEDIUM] THE STATUS RULE IS ABOUT THE COUNT, NOT ABOUT THE COUNT HAVING MOVED
  - says: THE STATUS RULE IS ABOUT THE COUNT, NOT ABOUT THE COUNT HAVING MOVED
- **resync_roll.py** `relabelled` — [MEDIUM] A ROLL ROW WITH NO RECORD FILE IS UNCHECKED, NOT AGREED
  - says: A ROLL ROW WITH NO RECORD FILE IS UNCHECKED, NOT AGREED
- **resync_roll.py** `dupes` — [MEDIUM] stores duplicate source filenames in a list
  - says: index every record file by its declared `source`
- **pipeline.py** `batch_settled` — [MEDIUM] the function is used to determine if a batch is settled (i.e., all entries are judged), and skips processing if true
  - says: was written to kill; that fix stopped batches closing over unjudged entries, but nothing reopened a batch that acquired unjudged entries afterwards.
- **mutate.py** `confirm` — [MEDIUM] the gates to be mutated
  - says: the gates to be confirmed
- **mutate.py** `gates` — [MEDIUM] the gates to be confirmed
  - says: the gates to be mutated
- **mutate.py** `os.walk` — [MEDIUM] copy files recursively
  - says: copy files recursively
- **mutate.py** `os.makedirs` — [MEDIUM] create state directory
  - says: create state directory
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Returns True if both qualifiers are None or their normalized forms are equal, but does not handle cases where one qualifier is None and the other is not.
  - says: Two names may only be compared if their qualifiers agree.
- **dashboard.py** `safety` — [MEDIUM] The function reads data from `state/drill_last.json` and calculates the age of the data, which aligns with the claim. However, the code does not explicitly state that the age is crucial for distinguishing between current and past data states.
  - says: The drill writes `state/drill_last.json` when it runs and this reports what it found and HOW OLD that is -- an age is not decoration here, it is the difference between "57 nets held" and "57 nets held, at some point, possibly before the change you are looking at".
- **address.py** `_index_name_is_placed_like_a_title` — [MEDIUM] The function checks if the index name is placed like a title, but the logic is flawed in how it handles pluralization and partial matches, leading to incorrect categorization of vocabulary vs title evidence.
  - says: The index entry sits inside the target: is it there as the title, or as vocabulary?
- **escalation.py** `clear` — [MEDIUM] clear() returns False for two different reasons, but the code treats them as the same event, leading to incorrect messages about the lift not happening.
  - says: PermissionError is caught alongside ValueError because `clear()` raises it for a non-person caller, and the two refusals are the same event to a reader: the lift did not happen and here is why.
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
