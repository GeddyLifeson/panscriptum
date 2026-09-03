# OVERWATCH

round 315  ·  last run 2026-09-03 16:28

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 292,446 inspected (deep scan as of round 313)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py

## What the model found in the code

**17 open** (3 high). Newest first.

- **descending_ladder.py** `rung_for_length` — [HIGH] Returns (rung, name) for sizes within the descending rungs, but returns (FOLD_RUNG, "Below the Fold") for sizes below the Planck length and (None, None) for sizes above the continental crust. However, the code's logic for determining the best rung is flawed because it starts with DESCENDING[0] (continental crust) and then iterates through the DESCENDING list, which is ordered from the largest to the smallest. This means that the code will incorrectly return the continental crust rung for sizes that are larger than the continental crust but smaller than the next rung (e.g., 5e6 m, which is larger than the continental crust's 1e6 m but smaller than the next rung's 1e5 m). The function's logic is flawed because it should iterate through the DESCENDING list in reverse order to find the correct rung.
  - says: Which descending rung does a given size belong to? Returns (rung, name).
- **verify_math.py** `check` — [HIGH] the key is not stable across runs due to using hash()
  - says: the same entity and passage still hit the same key IN A LATER PROCESS
- **verify_math.py** `silence.append_line` — [HIGH] append_line raises an exception when the file path is invalid
  - says: append_line reports failure rather than raising
- **entity_match.py** `qualifier_compatible` — [MEDIUM] Returns True if both qualifiers are None or their normalized forms are equal, but does not handle cases where one qualifier is None and the other is not.
  - says: Two names may only be compared if their qualifiers agree.
- **verify_math.py** `_open20i` — [MEDIUM] contains buckets that are not open unknowns
  - says: contains buckets that are open unknowns
- **verify_math.py** `_cb20i.UNRECOGNISED` — [MEDIUM] assigns the file path to the attribute
  - says: replaces the UNRECOGNISED path with a file
- **verify_math.py** `measure_bit_value` — [MEDIUM] is NOT the cumulative figure the stale docstring quoted
  - says: is NOT the cumulative figure the stale docstring quoted
- **verify_math.py** `measure_bit_value` — [MEDIUM] uses band_resolution, not the cumulative length
  - says: uses band_resolution, not the cumulative length
- **verify_math.py** `check` — [MEDIUM] the k-th burg holds P1/k, but the code compares it to a value that is the floor of P1/k, and the comparison is exact rather than using a tolerance
  - says: the k-th burg holds P1/k, independently recomputed
- **verify_math.py** `A.axis_score` — [MEDIUM] returns the clamped value at the band's floor
  - says: a firecracker and the band floor both read 0.0 — this is why NONE exists
- **policy.py** `ev_interesting` — [MEDIUM] not used after assignment
  - says: interesting feats files
- **catalogue_aurora.py** `update_rows` — [MEDIUM] the function is called and its return value is checked, but the error message is printed and the script exits with 1 if there's a refusal
  - says: this whole function exists to argue that a write verdict must never be discarded, and this was the one call in it that still did
- **workorders.py** `_fire` — [MEDIUM] appends to `filed` and may close orders
  - says: raises an order for a problem
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
