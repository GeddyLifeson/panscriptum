# OVERWATCH

round 138  ·  last run 2026-08-29 01:25

## Structure

- modules that will not import: **1**  — cascade_bridge: exited without a traceback, saying: live call -> FAILED
- files that will not parse: **2** of 270,644 inspected (deep scan as of round 133)  — state\gpu_lane\slot.1.json — cannot stat; state\snapshots\AppData\Local\Temp\sweep37probe_a76ncjt1\real.txt — cannot stat
- catalogued sources with no host: **8** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secret
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major

## What the model found in the code

**6 open** (2 high). Newest first.

- **gpu_lane.py** `_heartbeat` — [HIGH] Does not actually keep leases fresh; it was supposed to call _touch to refresh leases but does not do so.
  - says: Keep every lease this call holds fresh until the call finishes.
- **generate.py** `generate_job` — [HIGH] generate a job, but the function is not defined in this slice
  - says: generate a job
- **hostcheck.py** `add` — [MEDIUM] Adds to the grounded list if not speculative, but the function is called with speculative=True for some entries
  - says: Adds a host to either the speculative or grounded list
- **gpu_lane.py** `_take_slot` — [MEDIUM] Claims a lease by creating a file, but does not check if the lease is expired or not.
  - says: Claim one of MAX_SLOTS leases, or return None if they are all live.
- **gpu_lane.py** `_alive` — [MEDIUM] Treats unknown PIDs as alive, which contradicts the docstring's claim that dead PIDs should have their leases broken immediately.
  - says: Is this PID still running? A dead holder's lease is broken immediately.
- **generate.py** `save_json` — [MEDIUM] save_json is called with the failures dictionary, but the code does not handle the case where save_json might fail to write the file, leading to potential data loss without error h
  - says: save_json(cfg["paths"]["failures"], failures)

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
