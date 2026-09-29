# FIX_G5 (feats, foreman, gpu_lane, local_agent, overnight) - run #67

| order | verdict | how | net |
|---|---|---|---|
| 926b5f0f997b | FIXED | `feats._brace_end` returns `(j, closed)`; both callers trim the closer width only when closed | nets/926b5f0f997b.py |
| 888b8b52467a | FIXED | `resolve_hosts` and `evidence_for` land through `silence.write_json` (pid/thread temp) | nets/888b8b52467a.py |
| 2a5344d24132 | FIXED | `foreman._SCRIPT_RE` + `_foreign_prefix` / `_foreign_tree` are the one definition of "another tree"; used by `kill_duplicate_jobs`, `restart_reader`, `kill_stalled_job` | nets/2a5344d24132.py |
| 76598c5d0cdc | FIXED | `gpu_lane._expired` wraps the heartbeat `float()`; TypeError/ValueError answers expired | nets/76598c5d0cdc.py |
| 9310fefed227 | FIXED | `_take_slot` re-reads the slot and removes it only if it still equals the expired record | nets/9310fefed227.py |
| 9e59609b76b2 | FIXED | `t_find_symbol` collects `skipped_files`, adds them to `warning`, sets `unique` False when any exist | nets/9e59609b76b2.py |
| d6e486885673 | FIXED | remedies comment moved from above `RESTART_STAMP` to above `REMEDIES` | comment-only |
| 7fb8805a1501 | FIXED | overnight comment names `autostart.supervisor_alive` / `start_supervisor`, no line numbers | comment-only |

Every net returns True on the fixed tree and False with its `_revert.json` applied (checked by copying src to a temp dir).

## Questions / left alone
- 9e59609b76b2: `t_find_symbol` also skips the `deprecated` dir silently. That looks deliberate (retired code is not a live definition), so it is untouched and unreported in `skipped_files`.
- 9310fefed227: the same read-then-remove shape exists in the unreadable-and-stale branch (`_unreadable_and_stale` then `_remove_retry`). Not cited by the order, so unchanged. The fix narrows the window to one re-read; a file has no atomic compare-and-remove.
- 76598c5d0cdc: a garbage heartbeat now reclaims the slot even if its pid is alive, matching how a missing heartbeat already behaved (`or 0`). `_alive` treats an unparseable pid as alive, so the two corrupt-field policies differ; left as ordered.
- 2a5344d24132: a command line with a relative `src/read.py` (no drive prefix) cannot be judged and is treated as ours, same as `kill_duplicate_jobs`.
