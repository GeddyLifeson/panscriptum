# OVERWATCH

round 288  ·  last run 2026-09-02 19:14

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 289,770 inspected (deep scan as of round 283)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition
- NOT RUNNING: **0** autostart.py
- NOT RUNNING: **0** read.py

## What the model found in the code

**6 open** (0 high). Newest first.

- **recover_folder_records.py** `record_path` — [MEDIUM] the existing file wins where there is one, so a record written under the old 60-character cap is FOUND (and therefore correctly seen as already populated by the guard below) instead of being shadowed by a second file under the un-truncated name.
  - says: THE ROLL IS A SNAPSHOT; THE RECORD FOLDER IS THE TRUTH. `empty` was selected from SWEEP_ROLL.json as it stood when this process started, and the roll is written by SEVEN different scripts (four, in silence.write_json's older account of it; the count was already stale and the roll writes are compare-and-swapped now, but this snapshot is still a snapshot). If another writer -- the cloud session, ingest.py, resync_roll.py, or a concurrent run of this very tool -- landed real researched entries in that record since the snapshot, writing here would replace research with a truncated folder-mechanical transcription and mark the roll catalogued over it, with nothing in the output saying so. An unreadable file counts as populated: not knowing what is there is not evidence that nothing is, and this direction is the recoverable one.
- **prose_gate.py** `evidence_ok` — [MEDIUM] Uses floor_ok to check floor, but floor_ok returns False for floor <= 0, which is supposed to be MISCONFIGURED and refuse
  - says: Has this source been read enough to be worth writing about?
- **endpoint.py** `one` — [MEDIUM] returns None for HTTP errors and HTML bodies, but returns the body for non-HTML content
  - says: fetch raw content from a URL and return it if successful
- **escalation.py** `clear` — [MEDIUM] clear() returns False for two different reasons, but the code treats them as the same event, leading to incorrect messages about the lift not happening.
  - says: PermissionError is caught alongside ValueError because `clear()` raises it for a non-person caller, and the two refusals are the same event to a reader: the lift did not happen and here is why.
- **cascade_bridge.py** `selftest` — [MEDIUM] executes the live check
  - says: The live check is NOT dropped
- **ingest_doc.py** `mine` — [MEDIUM] mine(a.source) is called but its return value is not checked for the early stops conditions
  - says: mine(a.source) returns True only when every chunk was processed, and False on both of its early stops

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
