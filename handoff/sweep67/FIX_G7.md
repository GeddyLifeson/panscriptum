# FIX_G7 (run #67)

| order | verdict | how | net |
|---|---|---|---|
| 1e2e6aad5fca | FIXED | mutate._write_rulings lands via silence.replace_if_unchanged under a per-pid tmp; new _edit_rulings re-reads and re-applies on a lost race; rule/unrule use it | nets/1e2e6aad5fca.py |
| 59b534837fb2 | FIXED | (a) silence.note on the sandbox state-copy OSError; (b) live_before moved inside the try in _run_mutation so the sandbox is reaped | nets/59b534837fb2.py |
| 0620969b742d | FIXED | _lock_acquire re-reads LOCK and removes it only if it still equals the stale record; O_EXCL decides otherwise (microsecond read-then-remove window remains, marked ponytail) | nets/0620969b742d.py |
| 6093d3475efc | FIXED | file_orders gated on `stopped_at != i` in _session | nets/6093d3475efc.py |
| 599bfad87a6b | FIXED | overwatch.round_once digests the module before review() and uses it for seen and finding stamps | nets/599bfad87a6b.py |
| 2beb0a7fa5b3 | FIXED | suppressions._load returns ([], False) for non-dict rows, non-str detector/path, non-numeric or bool expires_at (an ABSENT key is still tolerated, as every reader defaults it) | nets/2beb0a7fa5b3.py |
| f8dd772a0273 | FIXED | silence.append_line docstring and the _lock_exclusive comment corrected (LK_LOCK blocks ~10 s, then writes unlocked and returns True); LK_NBLCK not adopted | comment-only |
| 98650e9d31d7 | FIXED | silence.swallow.__exit__ returns False for non-Exception exc_type; class NOT deleted | nets/98650e9d31d7.py |
| 969ebdbbda98 | FIXED | load_thread_graph records non-dict T1/T2 entries as unresolvable, raises ThreadGraphUnreadable for non-dict T2 or non-list T2 values (None still means no threads) | nets/969ebdbbda98.py |

Each net passes on the fixed source and returns False with its _revert.json applied to a copy of src/.
Questions: none. Design note: 2beb tolerates absent keys deliberately; the order asked for strictness on every row.
