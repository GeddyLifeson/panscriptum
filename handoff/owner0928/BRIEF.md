# Owner-directed "fix everything" session, 2026-09-28 — shared brief for every fixing agent

The owner (the person who owns this library) has told us, in chat, to FIX EVERYTHING in the work-order queue. That is the owner's ruling on every OWNER-routed order in your group: where an order offers options (a)/(b)/(c), TAKE THE OPTION THE FILING RUN RECOMMENDED ("this run's reading is ..."). Where no option was recommended, take the option that actually closes the fault while keeping data and history (fail closed, uncapped, reversible). Record in each resolution that it was decided under the owner's 2026-09-28 "fix everything" instruction and which option was taken.

## Where things are
- Kit: C:\Users\imarl\panscriptum-library-kit. Read CLAUDE.md there first (Hard Rules -1 and 0 especially).
- Python: C:/Users/imarl/miniconda3/python.exe with PYTHONIOENCODING=utf-8. NEVER the bare `py` launcher. NEVER run anything from C:\Users\imarl\panscriptum-export.
- The full queue as of session start: handoff/owner0928/queue.json (each order's full text is in `what` and `found_by`). Live queue: state/workorders.json.

## Absolute limits (the owner's instruction does NOT override these)
1. NEVER set or open `prose_enabled` or `step4_enabled`. Never weaken a gate (prose_gate, the halt, escalation). Tightening one in the fail-closed direction is allowed.
2. NEVER create accounts, enter passwords/tokens/API keys, or change credentials.
3. NO CAPS (Hard Rule 0): never truncate a roster/list/entry set.
4. Records are written ONLY through `pipeline.write_record` / `write_record_catalogue`; shared state lands via `silence.replace_retry`.
5. Do not delete data or history. If an option says "delete files", MOVE them to an archive directory instead (e.g. handoff/_archive/...) and say so. Deleting dead code inside a .py module is allowed when the order recommends it.
6. Never write regexes or backslashes through a shell heredoc; use the Edit/Write tools or chr().
7. DO NOT spawn subagents. DO NOT run the full `src/verify_math.py`, `src/drill.py`, `src/allsweep.py`, or `src/mutate.py` — the coordinator runs the battery once at the end, and two verify_math runs at once corrupt each other. You MAY run `src/drill.py --prove AREA "NET NAME" [--revert FILE.json]` for nets you add, targeted python snippets, `python -m pyflakes <file>`, and module self-tests.
8. Do not kill or restart daemons. Do not start long crawls/generation jobs; if an order's fix needs one (a re-catalogue, a re-read), prepare it and name the exact command in your report instead.

## Editing shared files — LOCK FIRST
Several agents are editing src/ at once. Before editing ANY file, take its lock and drop it as soon as that file's edit is done:
    python handoff/owner0928/lock.py take src/foo.py GROUPNAME
    ... edit ...
    python handoff/owner0928/lock.py drop src/foo.py GROUPNAME
Re-read the file after taking the lock (another agent may have changed it). Keep lock hold times short. drill.py and verify_math.py are the hottest files: batch all your edits to each into one lock hold.

## Every fix needs proof
- When you add or change a guard, add a drill net (or verify_math row) that attacks it, and PROVE it: `drill.py --prove AREA "NET" --revert revert.json` must print RED, and without --revert it must print HELD. Revert files are JSON [{"module": "x.py", "old": "...", "new": "..."}]; write them with the Write tool under handoff/owner0928/.
- pyflakes every file you touched.

## Closing orders
Close each order you fixed:
    python src/workorders.py --resolve <id> --how-file <path>
Write the --how text to a file with the Write tool first (never put order text on a command line). Say what changed, which option was taken under the owner's ruling, and how it was proven. If an order genuinely cannot be closed by code (e.g. it needs the owner to take an account action), do NOT close it; explain in your report exactly what the owner must do.

## Report
Write handoff/owner0928/REPORT_<GROUP>.md (full detail), then RETURN ONLY a compact summary (under 300 words): each order id -> closed / not closed (why), files touched, nets added and their RED/HELD proof, and any command the coordinator must run (long jobs, daemon bounces).
