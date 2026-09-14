# OVERWATCH

round 506  ·  last run 2026-09-14 04:50

## Structure

- modules that will not import: **0**
- files that will not parse: **0** of 304,616 inspected (deep scan as of round 505)
- catalogued sources with no host: **7** Curious DM Investigations (the Sharkin), Genuine Fantasy Press (Forgotten Secrets), JMBrew, Kobold Press (Midgard Heroes Handbook, Midgard Worldbook), Super Energy Apocalypse 1 & 2, aurora_mods (Way of the Inkmaster), and 1 more
- on the roll but never catalogued: **6** HAWX, Heaven's Lost Property, Lost Mines of Phandelver, Twilight Imperium, major live-action Disney films, the Witch Tradition

## What the model found in the code

**16 open** (6 high). Newest first.

- **policy.py** `main` — [HIGH] the code does not do
  - says: the code says it does
- **policy.py** `landed` — [HIGH] the value of `landed` is not used in the code
  - says: THE LANDED VERDICT IS PART OF THE ANSWER
- **pipeline.py** `blocks` — [HIGH] The code is using an or which short-circuits, leading to rest not being evaluated if with_feats has any entries
  - says: The code says it is combining with_feats and rest with a + to keep every part of the ranking the owner did allow
- **overnight.py** `_cmd_is_running` — [HIGH] Splits the fragment into parts and checks if the first part matches the script, but does not properly verify if the fragment is showing the script being run.
  - says: Does this command line show `fragment` BEING RUN, rather than merely mentioned?
- **onomast.py** `well_formed` — [HIGH] Implements seven constraints but the docstring claims it was meant to implement four, and three of the four original constraints were misattributed
  - says: Is this a name a Custos could say aloud and write down twice the same way?
- **mutate.py** `_lock_acquire` — [HIGH] Acquires a lock and writes a token to it, but does not release it.
  - says: Drop the lock, but only if it is still OURS.
- **policy.py** `write_json` — [MEDIUM] the function is called with the REPORT variable, which is the path to the JSON file, and the function is supposed to write the JSON to that file and then rename it
  - says: the console output is this run's, and `state/policy_report.json` is the only copy that outlives it
- **pipeline.py** `return 1` — [MEDIUM] returns 1 regardless of whether the phase is stalled or not, which may not correctly signal the state to the caller as intended
  - says: RETURN 1 (order 1f8e0f1bfb26). A stalled phase is exactly the condition `overnight.py:run()` needs to see in `p.returncode` -- it launches this file as a subprocess (`[pipeline.py, "--run"]`, via `overnight.STANDING`'s "pipeline" entry and `overnight.py`'s own `start("pipeline", ...)` call) and folds `p.returncode` straight into the cycle's health summary ("ok" iff returncode == 0). A bare `return` here used to make a mid-ladder stall READ AS "ok", identically to a cycle that finished every phase -- the same fault class order e8466cd6ed14 already fixed at `onomast.main()`, `reference.main()`, `genre.main()`, `sevenfold.main()` and `wh40k.main()` just not caught here because that sweep never visited pipeline.py.
- **pipeline.py** `spine_of` — [MEDIUM] return AD.spine_code_for(src) if it exists, else None
  - says: return AD.spine_code_for(src)
- **pipeline.py** `silence.replace_retry` — [MEDIUM] could never see one, and a refused rename left the PREVIOUS run's RUN_STATUS.md in place with its earlier counts and phase ladder
  - says: does not raise on a denial -- that is its contract
- **pipeline.py** `batch_settled` — [MEDIUM] The function is called to determine if a batch is settled, but the code's comment and the surrounding context suggest that the function's actual behavior may not align with the intended logic for handling growing entry lists.
  - says: A CLOSED BATCH IS NOT A CLOSED SPAN. The resume key is `source#start`, but the span it names is `entries[start:start+B]` -- and a record's entry list GROWS after entrypass has run over it (`ingest_doc.py` appends doc-derived entries through write_record_catalogue). So the tail batch silently widens under a key that is already in done_keys, and every entry appended past the old end is skipped forever: never categorised, never given a scale_note, never banded.
- **overnight.py** `_twin` — [MEDIUM] check if another instance of overnight.py is running
  - says: check if another supervisor is already running
- **mutate.py** `os.makedirs` — [MEDIUM] creates the directory if it does not exist
  - says: creates the directory
- **manifest_builder.py** `report_landed` — [MEDIUM] report_landed is assigned but never used beyond the check for its truth value
  - says: report_landed is the verdict on the report write
- **health.py** `return 1 if reopen_stranded(dry=not a.go) is None else 0` — [MEDIUM] return 1 if the result of reopen_stranded is None else 0
  - says: return 1 if the result of reopen_stranded is None else 0
- **feats.py** `main` — [MEDIUM] returns 0 or 1 based on the roll's success, but the comment claims it should follow the same pattern as `--hosts` and `resolve_hosts` which return 1 if _HOSTS_DENIED else 0 and exit nonzero on failure
  - says: the sibling branches in this same file already do it: `--hosts` twenty lines up returns `1 if _HOSTS_DENIED else 0`, and `resolve_hosts`'s own docstring promises "main() exits nonzero on it". `--roll` was the one place the pattern was never applied, even though `roll()` has always returned exactly the counters needed.

---

Written by `src/overwatch.py`. Structure is checked every round; the model reads modules that changed first, then whichever has gone longest unread. A finding stays open until the file it points at changes.
